import docker
from neo4j import GraphDatabase
import subprocess

client = docker.from_env()

uri = "bolt://localhost:7687" 
driver = GraphDatabase.driver(uri, auth=("neo4j", "test"))

def list_stacks():
    try:
        result = subprocess.run(
            ['docker', 'compose', 'ls'], 
            capture_output=True, text=True, check=True
        )
        lines = result.stdout.strip().split('\n')[1:]
        stacks = [line.split()[0] for line in lines]
        return stacks
    except subprocess.CalledProcessError as e:
        print(f"Error getting Docker stacks: {e}")
        print(f"stderr: {e.stderr}")
        print(f"stdout: {e.stdout}")
        return []

def create_stack(tx, stack_name):
    query = "MERGE (s:Stack {name: $name})"
    tx.run(query, name=stack_name)

def create_container(tx, container_name, image, stack_name):
    query = (
        "MERGE (c:Container {name: $name}) "
        "ON CREATE SET c.image = $image "
        "WITH c "
        "MATCH (s:Stack {name: $stack_name}) "
        "MERGE (s)-[:CONTAINS]->(c)"
    )
    tx.run(query, name=container_name, image=image, stack_name=stack_name)

def create_dependency(tx, src_container, dest_container):
    query = (
        "MATCH (a:Container {name: $src_name}), (b:Container {name: $dest_name}) "
        "MERGE (a)-[:DEPENDS_ON]->(b)"
    )
    tx.run(query, src_name=src_container, dest_name=dest_container)

def determine_stack_name(container_name, stacks):
    for stack in stacks:
        if stack in container_name:
            return stack
    return "unknown"

with driver.session() as session:
    # Liste as stacks
    stacks = list_stacks()
    if not stacks:
        print("No stacks found.")
        exit(1)
    
    containers = client.containers.list()
    container_map = {stack: [] for stack in stacks}

    for container in containers:
        container_name = container.name
        container_image = container.image.tags[0]
        stack_name = determine_stack_name(container_name, stacks)

        if stack_name != "unknown":
            container_map[stack_name].append(container_name)

            session.write_transaction(create_stack, stack_name)
            session.write_transaction(create_container, container_name, container_image, stack_name)

    for stack_name, containers_in_stack in container_map.items():
        if containers_in_stack:
            for i in range(len(containers_in_stack)):
                for j in range(i + 1, len(containers_in_stack)):
                    src_container = containers_in_stack[i]
                    dest_container = containers_in_stack[j]
                    session.write_transaction(create_dependency, src_container, dest_container)

driver.close()
