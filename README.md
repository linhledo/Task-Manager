# Task-Manager
Deployment Guide (Google Kubernetes Engine)
This guide explains how to run the Task Manager microservices application on Google Kubernetes Engine (GKE).

Prerequisites
Install and configure the following tools:

- Google Cloud CLI
- kubectl
- A Google Cloud project with billing enabled and the required GKE and Artifact Registry permissions

1. Authenticate with Google Cloud

Log in and select your Google Cloud project:

gcloud auth login
gcloud config set project YOUR_PROJECT_ID

Configure Docker to authenticate with Artifact Registry:

gcloud auth configure-docker australia-southeast1-docker.pkg.dev

2. Create a GKE cluster

Create an Autopilot cluster in the Sydney region:

gcloud container clusters create-auto task-manager-cluster \
  --location=australia-southeast1 \
  --project=YOUR_PROJECT_ID

If the cluster already exists, skip this step.

Configure kubectl to connect to the cluster:

gcloud container clusters get-credentials task-manager-cluster \
  --location=australia-southeast1 \
  --project=YOUR_PROJECT_ID

Verify the connection:

kubectl get nodes

3. Create the Kubernetes namespace

Create a dedicated namespace for the application:

kubectl create namespace task-manager

If the namespace already exists, skip this step.

4. Configure Kubernetes Secrets

Create a local .env file containing the environment variables required by the application, including SECRET_KEY and DB_PASSWORD.

Create the Kubernetes Secret from that file:

kubectl create secret generic task-manager-secrets \
  --from-env-file=.env \
  -n task-manager

Verify that the Secret exists:

kubectl get secrets -n task-manager

5. Create the database schema ConfigMap

From the project root, create a ConfigMap using the SQL schema:

kubectl create configmap task-manager-schema \
  --from-file=schema.sql=database/schema.sql \
  -n task-manager

Verify that it exists:

kubectl get configmap task-manager-schema -n task-manager

6. Deploy the application

Apply the Kubernetes manifests:

kubectl apply -f k8s/app.yaml

The manifest deploys the frontend, task service, user service, and PostgreSQL database.

7. Verify the deployment

Check the status of all application Pods:

kubectl get pods -n task-manager

Check the Services:

kubectl get services -n task-manager

Wait until all Pods show Running and the application containers are ready.

If a Pod fails to start, inspect its events and logs:

kubectl describe pod POD_NAME -n task-manager
kubectl logs POD_NAME -n task-manager

Replace POD_NAME with the name of the affected Pod.

8. Access the application

If the frontend Service uses LoadBalancer, retrieve its external IP:

kubectl get service frontend -n task-manager

Wait until an external IP appears in the EXTERNAL-IP column, then open:

http://EXTERNAL_IP

This assumes the Service exposes HTTP on port 80 and forwards traffic to the frontend container's port 5000. If a different Service port is configured, use the corresponding port in the URL.

9. Scale application services

Scale a Deployment by changing its replica count:

kubectl scale deployment/frontend \
  --replicas=2 \
  -n task-manager

Check the resulting Pods:

kubectl get pods -n task-manager

Repeat for other stateless services as required. Ensure that resource availability and service configuration support the chosen replica count.

10. Update and redeploy an image

After building and pushing a new image tag, update the corresponding image reference in k8s/app.yaml, then apply the manifest:

kubectl apply -f k8s/app.yaml

Monitor the rollout:

kubectl rollout status deployment/frontend -n task-manager

Replace frontend with the Deployment being updated.

To roll back a Deployment to its previous revision:

kubectl rollout undo deployment/frontend -n task-manager

11. Clean up cloud resources

When the application is no longer required, delete its Kubernetes resources:

kubectl delete -f k8s/app.yaml

If you no longer need the cluster, delete it to avoid ongoing cluster and workload charges:

gcloud container clusters delete task-manager-cluster \
  --location=australia-southeast1 \
  --project=YOUR_PROJECT_ID
