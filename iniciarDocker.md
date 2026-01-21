# Inicialización de docker para el servidor cloud

## 1. Terminiar y formatear los servicios

```bash
docker-compose down. || (Para eliminar los volumenes) docker compose down --volumes
docker image prune -a
docker compose up --build -d
```

## 2. Poner los datos en la base de datos

```bash
docker cp init.sql db:/tmp/init.sql
docker compose exec db sh -c "mysql -u cole_user -pEuLdLmDcNnQa12 cole_db < /tmp/init.sql"
```

## 3. Observar el comportamiento de los servicios

```bash
docker compose logs -f 
```

## 4.Entrar dentro del contenedor de server

```bash
docker exec -it server sh
```
