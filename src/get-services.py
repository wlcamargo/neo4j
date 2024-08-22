import docker

# Conecte-se ao Docker daemon
client = docker.from_env()

# Liste todos os contêineres em execução
containers = client.containers.list()

# Exibe informações sobre os contêineres
for container in containers:
    print(f"Nome: {container.name}, ID: {container.id}, Imagem: {container.image.tags}, Status: {container.status}")
