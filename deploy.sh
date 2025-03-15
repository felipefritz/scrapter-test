#!/bin/bash

# environment vars
PROJECT_ID="scraping-challenge-123"  
REGION="us-central1"
REPOSITORY="scraping-repo"
IMAGE_NAME="scraping-ingest"
IMAGE_TAG="latest"
JOB_NAME="scraping-job"


# use required api from gcp
gcloud services enable \
  artifactregistry.googleapis.com \
  run.googleapis.com


# create repo  Artifact Registry if not exists
echo "Verificando repositorio en Artifact Registry..."
if ! gcloud artifacts repositories describe $REPOSITORY --location=$REGION >/dev/null 2>&1; then
  echo "Creando repositorio en Artifact Registry..."
  gcloud artifacts repositories create $REPOSITORY \
    --repository-format=docker \
    --location=$REGION \
    --description="Repositorio para desafío técnico" \
    --quiet
else
  echo "El repositorio $REPOSITORY ya existe."
fi


# set up authentication with Artifact Registry
echo "Configurando autenticación de Docker..."
gcloud auth configure-docker $REGION-docker.pkg.dev


echo "Construyendo imagen Docker..."
docker build --platform linux/amd64 -t $REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/$IMAGE_NAME:$IMAGE_TAG .


echo "Subiendo imagen a Artifact Registry..."
docker push $REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/$IMAGE_NAME:$IMAGE_TAG
if [ $? -ne 0 ]; then
    echo "Error al subir la imagen. Verifica que estás autenticado y tienes permisos."
    exit 1
fi


# check if job exists in Cloud Run
echo "Verificando si el job $JOB_NAME existe en Cloud Run..."
if gcloud run jobs describe $JOB_NAME --region=$REGION >/dev/null 2>&1; then
    echo "El job $JOB_NAME ya existe. Actualizando el job..."
    # update image
    gcloud run jobs update $JOB_NAME \
      --image=$REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/$IMAGE_NAME:$IMAGE_TAG \
      --region=$REGION
else
    # create image
    echo "Creando el job $JOB_NAME..."
    gcloud run jobs create $JOB_NAME \
      --image=$REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/$IMAGE_NAME:$IMAGE_TAG \
      --tasks=1 \
      --max-retries=3 \
      --region=$REGION
fi


# start job in gcp run jobs
echo "Ejecutando job..."
gcloud run jobs execute $JOB_NAME --region=$REGION
echo "Proceso completado."
