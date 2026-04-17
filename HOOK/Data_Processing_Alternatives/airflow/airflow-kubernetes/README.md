# Airflow Kubernetes

- This directory contains resources and instructions for deploying Apache Airflow on Kubernetes, including building custom Docker images for Airflow and its dependencies, pushing them to a Harbor registry, and configuring the Kubernetes deployment.
- **Note**: This is for demonstration purposes only, and intended to introduce you to the process of deploying Airflow on Kubernetes. For production deployments, you should consider additional factors such as security, scalability, and monitoring.

Table of Contents

- [Assumptions](#assumptions)
- [Prerequisites](#prerequisites)
    - [Setting up Docker](#setting-up-docker)
    - [Setting up kubectl](#setting-up-kubectl)
    - [Setting up Git](#setting-up-git)
    - [Setting up Helm](#setting-up-helm)
    - [Harbor Registry Private Project Access](#harbor-registry-private-project-access)
- [Preparing Custom Docker Image used for deployment of Airflow on Kubernetes](#preparing-custom-docker-image-used-for-deployment-of-airflow-on-kubernetes)
    - [Airflow 3.1.7 Image](#airflow-317-image)
    - [Building Custom Airflow Image (Airflow 3.1.7)](#building-custom-airflow-image-airflow-317)
    - [Pushing Custom Airflow Image to Harbor Registry](#pushing-custom-airflow-image-to-harbor-registry)
- [Installing Airflow Kubernetes](#installing-airflow-kubernetes)
    - [Setup Kubernetes Cluster](#setup-kubernetes-cluster)
    - [Setup Kubernetes Dashboard (Optional)](#setup-kubernetes-dashboard-optional)
    - [Check kubectl access to the cluster](#check-kubectl-access-to-the-cluster)
    - [Create Namespace for Airflow](#create-namespace-for-airflow)
    - [Create Secret for Harbor Registry](#create-secret-for-harbor-registry)
    - [Helm Setup](#helm-setup)
    - [cert-manager Setup](#cert-manager-setup)
    - [Create ClusterIssuers](#create-clusterissuers)
    - [Configure DNS](#configure-dns)
    - [PVC Permissions for DAGs](#pvc-permissions-for-dags)
    - [Check override-values.yaml : Custom Image](#check-override-valuesyaml--custom-image)
    - [Check override-values.yaml : Ingress Configuration](#check-override-valuesyaml--ingress-configuration)
    - [Check override-values.yaml : Git Sync Configuration](#check-override-valuesyaml--git-sync-configuration)
    - [Deploy Airflow Using Helm](#deploy-airflow-using-helm)
    - [Check the status of the Airflow deployment](#check-the-status-of-the-airflow-deployment)
- [Troubleshooting](#troubleshooting)
    - [Check the status of the Airflow pods](#check-the-status-of-the-airflow-pods)
    - [Check the logs of a specific pod (e.g., the API server pod)](#check-the-logs-of-a-specific-pod-eg-the-api-server-pod)
    - [Check the events in the airflow namespace for any errors or warnings](#check-the-events-in-the-airflow-namespace-for-any-errors-or-warnings)
    - [Check all events in the cluster for any issues related to the Airflow deployment](#check-all-events-in-the-cluster-for-any-issues-related-to-the-airflow-deployment)
    - [Check ingress resources and events if you encounter issues with the ingress](#check-ingress-resources-and-events-if-you-encounter-issues-with-the-ingress)
    - [Starting from scratch : Delete the namespace and all resources within it, then reinstall Airflow](#starting-from-scratch--delete-the-namespace-and-all-resources-within-it-then-reinstall-airflow)
    - [Helm uninstall and force delete pods if necessary](#helm-uninstall-and-force-delete-pods-if-necessary)
- [Connecting to Airflow User Inteface : Check Access and Health](#connecting-to-airflow-user-inteface--check-access-and-health)
    - [Change Airflow Admin Password](#change-airflow-admin-password)
    - [Check Health of Airflow Components](#check-health-of-airflow-components)

    
## Assumptions

- This guide assumes you have a basic understanding of Docker, Kubernetes, and Helm.
- It also assumes you have access to a Kubernetes cluster where you can deploy Airflow, and that you have the necessary permissions to create namespaces, secrets, and deploy applications using Helm.

## Prerequisites

- Before you begin, ensure you have the following prerequisites in place:
    - Docker & Docker Compose
    - kubectl (for Kubernetes operations)
    - Git
    - Helm (for deploying Airflow on Kubernetes)
    - Access to the Destination Earth Data Lake, Harbor registry (e.g., `registry.central.data.destination-earth.eu`) with permissions to push images

### Setting up Docker

- Install Docker on your local machine or a VM that you will use for building and pushing Docker images. Follow the official Docker installation guide for your operating system: https://docs.docker.com/get-docker/

### Setting up kubectl

- Install kubectl, the command-line tool for interacting with Kubernetes clusters. Follow the official kubectl installation guide: https://kubernetes.io/docs/tasks/tools/install-kubectl/

### Setting up Git

- Ensure you have Git installed for version control and managing your code. Follow the official Git installation guide: https://git-scm.com/book/en/v2/Getting-Started-Installing-Git

### Setting up Helm

- Helm is a package manager for Kubernetes that simplifies the deployment of applications. You can install Helm by following the official Helm installation guide: https://helm.sh/docs/intro/install/

### Harbor Registry Private Project Access

- Login to Harbor at https://registry.central.data.destination-earth.eu/ using your DESP (Destination Earth Platform) credentials.
- If you don't have a project already, create a new project (e.g., `[organisation]_[name]_private`) to host your repositories/images.

    - Click on the Robot Accounts tab in your project and create a new robot account with push permissions. Note the generated username and password for Docker login.

    - The different permissions can be set for the robot account, but for pushing images, ensure it has at least "push" permissions on the repository.

        - "Create Tag" allows the robot to create new tags in the repository.
        - "Delete Tag" allows the robot to delete existing tags in the repository.
        - "List Tag" allows the robot to list tags in the repository.
        - "List Repository" allows the robot to list repositories in the project.
        - "Push Repository" allows the robot to push images to the repository.
        - "Delete Repository" allows the robot to delete the repository itself.
        - "Read Artifact" allows the robot to read artifacts in the repository.
        - "List Artifact" allows the robot to list artifacts in the repository.
        - "Delete Artifact" allows the robot to delete artifacts in the repository.
        - "Create Artifact Label" allows the robot to create labels for artifacts in the repository.
        - "Delete Artifact Label" allows the robot to delete labels for artifacts in the repository.
        - "Pull Repository" allows the robot to pull images from the repository.
        - "Create Scan" allows the robot to initiate vulnerability scans on images in the repository.
        - "Stop Scan" allows the robot to stop ongoing vulnerability scans on images in the repository.

- With a robot account created and the appropriate permissions set, you can use the generated credentials to log in to the Harbor registry from your terminal and push Docker images as needed for your Airflow deployment on Kubernetes.


## Preparing Custom Docker Image used for deployment of Airflow on Kubernetes

- In this section we will build a custom image based on Apache Airflow 3.1.7, this will include additional dependencies making sure they are available for your DAGs (e.g. python libraries or supporting code)
- This image will be pushed to a Harbor registry ready to be used in the Helm chart deployment for Airflow on Kubernetes.

### Airflow 3.1.7 Image

- On a VM with Docker installed, navigate to the directory containing the Dockerfiles and build the images as needed.
- Here we build a custom Airflow image based on the official Apache Airflow image, adding any necessary dependencies via a `requirements.txt` file.
    - This will be used in the helm chart deployment for Airflow on Kubernetes.


### Building Custom Airflow Image (Airflow 3.1.7)

- Here is an extract of the Dockerfile in this directory used to build the custom Airflow image based on Apache Airflow 3.1.7, with additional dependencies specified in a `requirements.txt` file.

```dockerfile
# Use the official Airflow image as the base
FROM apache/airflow:3.1.7
# Set environment variables for Airflow configuration
ENV AIRFLOW_VERSION=3.1.7
# Enable the experimental API for Airflow 3.x this is mainly to activate the API with basic auth. This will allow us to trigger DAGs remotely (e.g. with python code or client in a Jupyter Notebook)
ENV AIRFLOW__API__AUTH_BACKENDS="airflow.api.auth.backend.basic_auth"
# Install additional Python dependencies if needed
COPY requirements.txt /
RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" -r /requirements.txt

```

- To build the Airflow 3.1.7 image, run the following command in the terminal from the directory containing the Dockerfile:

```bash

# Build the Airflow 3.1.7 image: See Dockerfile for details
docker build -f Dockerfile -t destine_datalakelab_airflow3:latest .

```

### Pushing Custom Airflow Image to Harbor Registry

```bash

# Logout of registry if you are currently logged in with different credentials or want to switch accounts
docker logout registry.central.data.destination-earth.eu

# You can connect to your registry using your Robot Account credentials as follows:
docker login registry.central.data.destination-earth.eu

# Example for Airflow 3.1.7. Tag the image with the registry path and push it to Harbor
docker tag destine_datalakelab_airflow3:latest registry.central.data.destination-earth.eu/[YOUR_HARBOR_PROJECT]/[YOUR_IMAGE_NAME]:latest

# Push the tagged image to the registry
docker push registry.central.data.destination-earth.eu/[YOUR_HARBOR_PROJECT]/[YOUR_IMAGE_NAME]:latest

```






## Installing Airflow Kubernetes

- Now that we have the custom Airflow image built and pushed to the registry, we can use it in our Kubernetes deployment of Airflow. This will typically involve updating the Helm chart values to point to our custom image and ensuring that any necessary configurations (e.g., environment variables, volume mounts) are set up correctly.

### Setup Kubernetes Cluster

- For help setting up a Kubernetes cluster, you can refer to our main documentation at

    - [kubernetes](https://destine-data-lake-docs.data.destination-earth.eu/en/latest/dedl-big-data-processing-services/Islet-service/kubernetes/kubernetes.html)
    - [How to Create a Kubernetes Cluster Using OpenStack Magnum](https://destine-data-lake-docs.data.destination-earth.eu/en/latest/dedl-big-data-processing-services/Islet-service/kubernetes/How-to-Create-a-Kubernetes-Cluster-Using-OpenStack-Magnum/How-to-Create-a-Kubernetes-Cluster-Using-OpenStack-Magnum.html)


### Setup Kubernetes Dashboard (Optional)

- For easier management of your Kubernetes cluster, you could for example set up the Kubernetes Dashboard. This provides a web-based interface for managing your cluster resources, including deployments, services, and more.

    - Follow the official Kubernetes Dashboard installation guide: https://kubernetes.io/docs/tasks/access-application-cluster/web-ui-dashboard/


### Check kubectl access to the cluster

- Before proceeding with the deployment of Airflow on Kubernetes, it's important to verify that you have access to the Kubernetes cluster and that your `kubectl` command is properly configured. You can check your access by running the following command:

```bash
# Check access to the Kubernetes cluster
kubectl cluster-info

# List all resources in all namespaces to verify access
kubectl get all -A

```

### Create Namespace for Airflow


- Before deploying Airflow on Kubernetes, you need to create a namespace for Airflow

```bash

kubectl create namespace airflow

```

### Create Secret for Harbor Registry

- To pull the Airflow image from your private Harbor registry, you need to create a Docker registry secret in Kubernetes. This secret will allow Kubernetes to authenticate with the Harbor registry and pull the necessary images for your Airflow deployment. You can create the secret using the following command, replacing the placeholders with your actual Harbor registry credentials:

```bash

# Create a Docker registry secret for Harbor registry access
kubectl create secret docker-registry harborcred --docker-server=registry.central.data.destination-earth.eu --docker-username='[REPLACE WITH YOUR ROBOT USERNAME]' --docker-password='[REPLACE WITH YOUR ROBOT PASSWORD]' --namespace=airflow


```

### Helm Setup

- Assure helm is installed and configured correctly. You can check the version of Helm and ensure it's working with your Kubernetes cluster by running:

```bash

# Check Helm version
helm version

# Check Helm repositories
helm repo list

# Add the Apache Airflow Helm repository
helm repo add apache-airflow https://airflow.apache.org

# Update your local Helm chart repository cache
helm repo update

# List all available versions of the Apache Airflow Helm chart
helm search repo apache-airflow --versions

```

We can see that the lates version of the Apache Airflow Helm chart is 1.18.0, which corresponds to Airflow 3.0.2. You can choose to install this version or any previous version based on your requirements.

- Note: We can override the version of of Airflow installed using the override-values.yaml file (we will update version 3.0.2 to 3.1.7 in the override-values.yaml file)

```bash

eouser@xxxx$ helm search repo apache-airflow --versions
NAME                    CHART VERSION   APP VERSION     DESCRIPTION                                       
apache-airflow/airflow  1.18.0          3.0.2           The official Helm chart to deploy Apache Airflo...
apache-airflow/airflow  1.17.0          3.0.2           The official Helm chart to deploy Apache Airflo...
apache-airflow/airflow  1.16.0          2.10.5          The official Helm chart to deploy Apache Airflo...
...


```

### cert-manager Setup

- cert-manager is a Kubernetes add-on that automates the management and issuance of TLS certificates from various issuing sources. It ensures that your applications can securely communicate over HTTPS by automatically obtaining and renewing certificates. To set up cert-manager in your Kubernetes cluster, you can use Helm to install it. Here are the steps to install cert-manager:
- See the official cert-manager documentation for more details: https://cert-manager.io/docs/installation/helm/

```bash

# See https://cert-manager.io/docs/installation/helm/

# Add the Jetstack Helm repository, which contains the cert-manager chart
helm repo add jetstack https://charts.jetstack.io

# Update your local Helm chart repository cache to include the latest charts from Jetstack
helm repo update

# List all available versions of the cert-manager Helm chart
helm search repo jetstack --versions

eouser@xxxx$ helm search repo jetstack --versions
NAME                                    CHART VERSION   APP VERSION     DESCRIPTION                                       
jetstack/cert-manager                   v1.19.3         v1.19.3         A Helm chart for cert-manager                     
jetstack/cert-manager                   v1.19.2         v1.19.2         A Helm chart for cert-manager                     
jetstack/cert-manager                   v1.19.1         v1.19.1         A Helm chart for cert-manager                     
jetstack/cert-manager                   v1.19.0         v1.19.0         A Helm chart for cert-manager        


helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --version v1.19.2 \
  --set crds.enabled=true


```

- Expected output:

```bash

eouser@xxxx$ helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --version v1.19.2 \
  --set crds.enabled=true
NAME: cert-manager
LAST DEPLOYED: Fri Feb 13 16:08:59 2026
NAMESPACE: cert-manager
STATUS: deployed
REVISION: 1
TEST SUITE: None
...

```

- Check that cert-manager is running correctly by listing the pods in the `cert-manager` namespace:

```bash 

# List pods in the cert-manager namespace
kubectl get pods -n cert-manager

```

- Expected output:

```bash

NAMESPACE       NAME                                                       READY   STATUS    RESTARTS   AGE
cert-manager    pod/cert-manager-7ff7f97d55-kgw5v                          1/1     Running   0          2m25s
cert-manager    pod/cert-manager-cainjector-59bb669f8d-xlrkz               1/1     Running   0          2m25s
cert-manager    pod/cert-manager-webhook-59bbd786df-nddqr                  1/1     Running   0          2m25s

```

### Create ClusterIssuers

- ClusterIssuers are Kubernetes resources that define how certificates should be issued for your applications. They specify the certificate authority (CA) and the method of obtaining certificates, such as using Let's Encrypt. By creating ClusterIssuers, you can automate the process of obtaining and renewing TLS certificates for your Airflow deployment, ensuring secure communication between your services. You can create ClusterIssuers using YAML manifests that define the configuration for Let's Encrypt or any other CA you choose to use.

- In the initials step you might want to apply the staging issuer for testing purposes, and then switch to the production issuer once you have verified that everything is working correctly.
- The following commands will apply the ClusterIssuer configurations for both production and staging environments. The production issuer will be used for obtaining real certificates from Let's Encrypt, while the staging issuer can be used for testing and development purposes without hitting rate limits.

```bash
# Apply production issuer
kubectl apply -f cluster-ingress-prod.yml

# Apply staging issuer (for testing)
kubectl apply -f cluster-ingress-staging.yml

```
### Configure DNS

Note: For our demonstraion, we have used Islet (OpenStack) DNS Zone to create the necessary DNS records. You will need to create similar DNS records in your own DNS provider to point to your Kubernetes cluster's ingress controller.

- We will want to access the Airflow web interface through a custom domain name, so we need to configure DNS to point to our Kubernetes cluster's ingress controller. 

  - Using a DNS A record, we can map a domain name (e.g., `airflow.[YOUR-TENANT-NAME].[YOUR-DATABRIDGE-SITE].data.destination-earth.eu`) to the IP address of the ingress controller in our Kubernetes cluster. This allows us to access the Airflow web interface using a user-friendly URL instead of an IP address.
  
  - Alternatively, we can use a DNS CNAME record. A CNAME record allows us to alias one domain name to another. 

We will create a DNS A record pointing to your Kubernetes cluster's ingress controller: 123.45.678.90
- Example: `airflow.[YOUR-TENANT-NAME].[YOUR-DATABRIDGE-SITE].data.destination-earth.eu` -> 123.45.678.90

We will also create a CAA record to allow Let's Encrypt to issue certificates for our domain:
- type: CAA
- name: [YOUR-TENANT-NAME].[YOUR-DATABRIDGE-SITE].data.destination-earth.eu. # at the level of your dns zone for your tenant
- record: 0 issue letsencrypt.org

### PVC Permissions for DAGs

- Here we see how to set the necessary permissions for Airflow to create Persistent Volume Claims (PVCs) dynamically. This is important for Airflow to be able to store data and logs persistently in the Kubernetes cluster. By applying the RBAC role and role binding, we grant Airflow the necessary permissions to manage PVCs, which allows it to create and use persistent storage as needed for its operations.

- To allow DAGs to create Persistent Volume Claims (PVCs) dynamically:

```bash
# Apply RBAC role for PVC permissions
kubectl apply -f pvc-role.yml

# Apply role binding
kubectl apply -f pvc-rolebinding.yml
```

### Check override-values.yaml : Custom Image

- The `override-values.yaml` file contains the configuration settings for the Airflow deployment on Kubernetes. It is important to ensure that the image repository and tag are set correctly to point to your custom Airflow image in your private Harbor registry. Additionally, you need to verify that the ingress configuration is set up to use the correct hostname and TLS settings for your deployment.

- Here we see how to set the custom image created previously

```yaml

# This section specifies the custom Docker image for Airflow that will be pulled from the private Harbor registry. 
# The repository and tag should match the image you have built and pushed to your Harbor registry. 
# The pull policy is set to "Always" to ensure that Kubernetes always pulls the latest version of the image when deploying or updating Airflow.

images:
  airflow:
    repository: registry.central.data.destination-earth.eu/[YOUR_HARBOR_PROJECT]/[YOUR_IMAGE_NAME] # Replace with your Harbor registry path and image name
    tag: latest
    #pullPolicy: IfNotPresent
    pullPolicy: Always

```

### Check override-values.yaml : Ingress Configuration

- Here we see which cluster issuer we are using for the ingress and the hostname for the web ingress, this should match the DNS record created in the previous step.

```yaml

# Note: in airflow 3.0.2, the ingress configuration is under the apiServer section, which is different from previous versions where it was under the web section. Make sure to adjust the configuration accordingly based on the version of Airflow you are using.

ingress:
  apiServer:
    enabled: true
    annotations:
      cert-manager.io/cluster-issuer: "letsencrypt-prod"
    ingressClassName: nginx

    # The path for the API server Ingress
    path: "/"
    # The pathType for the above path (used only with Kubernetes v1.19 and above)
    #pathType: "ImplementationSpecific"
    pathType: "Prefix"

    #hosts: []
    hosts:
      # The hostname for the API server Ingress (templated)
      - name: "airflow.[YOUR-TENANT-NAME].[YOUR-DATABRIDGE-SITE].data.destination-earth.eu"

        # configs for API server Ingress TLS
        tls:
          # Enable TLS termination for the API server Ingress
          enabled: true
          # the name of a pre-created Secret containing a TLS private key and certificate
          secretName: "airflow-tls"

```


### Check override-values.yaml : Git Sync Configuration

- Here we see how to configure Git Sync to sync DAGs from a private GitHub repository. This involves enabling Git Sync, specifying the repository URL, branch, and SSH key secret for authentication. By setting up Git Sync, you can ensure that your DAGs are automatically updated in Airflow whenever changes are made to the specified GitHub repository, allowing for seamless integration and version control of your DAGs.
- For reference see: [Mounting DAGs from a private GitHub repo](https://airflow.apache.org/docs/helm-chart/stable/manage-dag-files.html#using-git-sync)

1. We will first create a private GitHub repository to store our DAGs. This repository will be used as the source for syncing DAGs into Airflow using Git Sync.
2. Create ssh key pair (private and public) that will be used for authentication with GitHub. The private key will be stored in a Kubernetes Secret, while the public key will be added as a deploy key in your GitHub repository.
  - ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
  - copy the public key (e.g., id_rsa_github_dags.pub) and add it as a deploy key in your GitHub repository with read access. This allows Git Sync to authenticate with GitHub and access the repository securely.
    - e.g. xclip -selection clipboard < ~/.ssh/id_rsa_github_dags.pub
3. In you repostitory navigate to Setting > Deploy Keys > Add deploy key. Here you will add the public SSH key that will be used by Git Sync to authenticate with GitHub and access the repository securely.  
4. You now need to convert teh private ssh key to a base64 string
  - base64 <my-private-ssh-key> -w 0 > temp.txt
  - copy the content of temp.txt and use it in the `override-values.yaml` file. Paste it to extraSecrets > airflow-ssh-secret > data > gitSshKey

- To sync DAGs from a private GitHub repository, configure Git Sync in your `override-values.yaml`:




```bash

# Git Sync configuration to sync DAGs from a private GitHub repository.
# This configuration enables Git Sync, specifying the repository URL, branch, and SSH key secret for authentication.

# You will need to create a GitHub repository containing your DAGs and set up SSH key authentication to allow Git Sync to access the repository securely. The SSH key should be stored in a Kubernetes Secret, which is referenced in the configuration below.

dags:
  gitSync:
    enabled: true
    repo: git@github.com:[YOUR_GITHUB_USERNAME]/[YOUR_GITHUB_REPOSITORY].git # Replace with your private GitHub repository URL
    branch: main
    subPath: "dags" # Good practice. This is the path within the repository where your DAGs are located. It allows you to organize your repository and specify exactly where Airflow should look for DAG files.
    sshKeySecret: airflow-ssh-secret # Reference to the Kubernetes Secret containing the SSH key for authentication
extraSecrets:
  airflow-ssh-secret:
    data: |
      gitSshKey: '[base64-encoded-ssh-key]' # Replace with your base64-encoded SSH private key for GitHub authentication
env:
  - name: AIRFLOW__CORE__LOAD_EXAMPLES
    value: "True"
    
```


### Deploy Airflow Using Helm

- To deploy Airflow on Kubernetes using Helm, you can use the following command. This command will upgrade or install Airflow with the specified configuration, including loading example DAGs and syncing DAGs from a private GitHub repository.

```bash
# Note we do not create the namespace here as we have already created it in the previous steps (see pre-requisites)
# The --version flag is optional, you can specify it to install a specific version of the Airflow Helm chart. If you omit it, Helm will install the latest version available in the repository.
helm upgrade --install airflow apache-airflow/airflow \
  --namespace airflow \
  -f override-values.yaml

# Here we specify the version of the Airflow Helm chart to install (1.18.0 in this case). This ensures that we are installing a specific version of Airflow that is compatible with our configuration and requirements. You can choose to install a different version if needed, but make sure to check the compatibility of your configuration with the chosen version.
helm upgrade --install airflow apache-airflow/airflow \
  --namespace airflow \
  --version 1.18.0 \
  -f override-values.yaml

# Alternatively, you can pull the Helm chart locally, customize it if needed, and then install it from the local directory. This allows you to have more control over the chart and make any necessary modifications before deploying Airflow.
cd custom

# Pull the specified version of the Airflow Helm chart and extract it to a local directory named "airflow"
helm pull apache-airflow/airflow --version 1.18.0 --untar

# Install Airflow using the local Helm chart with the specified configuration
helm upgrade --install airflow ./airflow -n airflow -f override-values.yaml

```
### Check the status of the Airflow deployment

- After deploying Airflow, you can check the status of the deployment to ensure that all components are running correctly. You can use the following command to check the status of the Airflow release in the specified namespace:

```bash
# Check the status of the Airflow release in the airflow namespace
helm status airflow -n airflow

# Check the status of all Airflow pods in the airflow namespace
kubectl get pods -n airflow

```

## Troubleshooting

- You may encounter issues during the deployment of Airflow on Kubernetes, such as pods being stuck in a pending or terminating state, or issues with the ingress configuration. Here are some troubleshooting steps you can take to resolve common issues:

### Check the status of the Airflow pods

```bash

# Check the status of all Airflow pods in the airflow namespace
kubectl get pods -n airflow

```
### Check the logs of a specific pod (e.g., the API server pod)

```bash

# Check the logs of a specific pod in the airflow namespace
kubectl logs -n airflow <pod-name>

```

### Check the events in the airflow namespace for any errors or warnings

```bash
# Check events in the airflow namespace for any errors or warnings
kubectl get events -n airflow
```

### Check all events in the cluster for any issues related to the Airflow deployment

```bash
# Check all events in the cluster for any issues related to the Airflow deployment
kubectl get events --all-namespaces
```

### If you encounter issues with the ingress, check the status of the ingress resources and the associated events

```bash
# Check the status of the ingress resources in the airflow namespace
kubectl get ingress -n airflow

# Check events related to the ingress resources in the airflow namespace
kubectl get events -n airflow --field-selector involvedObject.kind=Ingress

# Check events related to the ingress resources in all namespaces
kubectl get events --all-namespaces --field-selector involvedObject.kind=Ingress

# Check the logs of the ingress controller pod for any errors related to the Airflow ingress
kubectl logs -n ingress-nginx <ingress-controller-pod-name>

# Check certificate requests in the airflow namespace to see if there are any issues with certificate issuance for the Airflow ingress
kubectl get certificaterequests -n airflow

# Check the Challenges and Certificates created by cert-manager for the Airflow ingress
kubectl get challenges -n airflow
kubectl get certificates -n airflow

```

### Starting from scratch : Delete the namespace and all resources within it, then reinstall Airflow

```bash

# Delete the airflow namespace and all resources within it
kubectl delete namespace airflow

# Reinstall Airflow using Helm
helm upgrade --install airflow apache-airflow/airflow \
  --namespace airflow \
  -f override-values.yaml

```

### Helm uninstall and force delete pods if necessary

- Instead of deleting the entire namespace, you can also choose to uninstall Airflow using Helm and then force delete any pods that are stuck in a terminating state. This allows you to clean up the Airflow deployment without affecting other resources in the namespace.


```bash
# First helm list to check the status of the Airflow release
helm list -n airflow

# Uninstall Airflow using Helm
helm uninstall airflow -n airflow

```

- If pods are stuck, you can try this...

```bash

# Check the status of all Airflow pods in the airflow namespace
kubectl get pods -n airflow

# With Airflow 3.0.2, we have noticed that the redis pod and the migration pod can sometimes get stuck in a terminating state due to issues with PVCs. If this happens, you can try deleting these pods manually to allow them to be recreated by the Airflow deployment.
kubectl delete pod airflow-redis-0 -n airflow
kubectl delete pod airflow-run-airflow-migrations-wwld4 -n airflow

```

- To force delete a pod that is stuck in a terminating state, you can use the following command. This will immediately remove the pod from the cluster, allowing it to be recreated by the Airflow deployment.

```bash

kubectl delete pod airflow-redis-0 -n airflow --grace-period=0 --force

```

## Connecting to Airflow User Inteface : Check Access and Health

- Once Airflow is deployed and running, you can access the Airflow web interface using the hostname you configured in your ingress (e.g., `https://airflow.[YOUR-TENANT-NAME].[YOUR-DATABRIDGE-SITE].data.destination-earth.eu`). You can log in using the default credentials (username: `admin`, password: `admin`) or any credentials you have set up during the deployment process.

- Check that https://airflow.[YOUR-TENANT-NAME].[YOUR-DATABRIDGE-SITE].data.destination-earth.eu is accessible and that you can log in to the Airflow web interface using the default credentials (admin/admin).

  - It is recommended to change the default admin password after logging in for the first time to ensure the security of your Airflow deployment. You can do this through the Airflow web interface or by executing a command inside the API server pod, as described in the next section.
  - Also as admin you may create additional users with different roles and permissions to manage access to the Airflow web interface and its features. This allows you to control who can view and modify your Airflow deployment, ensuring that only authorized users have access to sensitive information and critical operations.

    - **Admin** roles: have full access to all features and settings in Airflow, including the ability to manage users, DAGs, and connections.
    - **User** roles: have limited access to Airflow features, typically restricted to viewing and managing their own DAGs and tasks, without the ability to modify global settings or manage other users.
    - **Op** roles: have permissions to view and manage DAGs and tasks, but do not have access to user management or global settings. This role is often used for operators who need to monitor and manage DAGs without having administrative privileges.
    - **Viewer** roles: have read-only access to the Airflow web interface, allowing them to view DAGs, tasks, and logs without the ability to make any changes or modifications.
    - **Public** roles: have very limited access, typically only able to view the Airflow web interface without any permissions to view DAGs, tasks, or logs. This role is often used for unauthenticated users or for public-facing Airflow deployments.

### Change Airflow Admin Password

- You can change the Airflow admin password by executing a command inside the API server pod. This allows you to securely update the admin password without having to modify any configuration files or redeploy Airflow. By using the `airflow users reset-password` command, you can set a new password for the admin user, ensuring that your Airflow deployment remains secure and accessible only to authorized users.

```bash

# Check the status of all Airflow pods in the airflow namespace to identify the API server pod
kubectl get pods -n airflow

# Once you have identified the API server pod (e.g., airflow-api-server-85f4696668-ct5s8), you can execute the following command to reset the admin password:
kubectl exec -it airflow-api-server-85f4696668-ct5s8 -n airflow -- bash

# Inside the API server pod, run the following command to reset the admin password:
airflow users reset-password \
  --username admin \
  --password '[YOUR_NEW_ADMIN_PASSWORD]' 

```

### Check Health of Airflow Components

- After logging into the Airflow web interface, you can check the health of the Airflow components
  - On the home page when connected as admin you will see MetaDatabase, Scheduler, Triggerer, and Dag Processor. All of these should be healthy (green check mark). If any of them are unhealthy (red cross), it indicates that there is an issue with that component, and you may need to investigate further by checking the logs of the corresponding pods in Kubernetes.

### Check that the DAGs are syncing correctly from the GitHub repository

- Also on the home page, at the top, you will see Dag Import Errors. Check that there are no import errors. This can just indicate that the DAGs are not compliant with the Airflow version you are using.

## Connecting to Airflow User Inteface : Run a DAG and check the logs

- To run a DAG in Airflow, you can trigger it manually from the Airflow web interface. Once the DAG is triggered, you can monitor its execution and check the logs for any issues or errors that may arise during the execution of the tasks within the DAG. This allows you to ensure that your DAGs are running correctly and to troubleshoot any problems that may occur during their execution.

### Trigger a DAG manually from the Airflow web interface

- To trigger a DAG manually from the Airflow web interface, follow these steps:
  1. Log in to the Airflow web interface using your credentials.
  2. Navigate to the "DAGs" tab to see the list of available DAGs. (Search for the 'tutorial' DAG if you are using the example DAGs)
  3. Find the DAG you want to trigger and click on the "Trigger Dag" button (usually represented by a play icon) next to the DAG name.
  4. Confirm the trigger action if prompted.

### Check the logs and the code of the triggered DAG

- In the left pane assure you are in grid view. 

  1. Click on the rightmost vertical column which indicates a given 'run' of the DAG.

  2. In the right pane, you will see the list of tasks for that DAG run. Click on a task to view its logs. (e.g. print_date task)

  3. You will see a number of tabs associated with that task. Let us just focus on the most important ones for troubleshooting and debugging (Logs, XCom and Code)

      - In the `Logs` tab, you can see the logs for that task execution. Check the logs for any errors or issues that may have occurred during the execution of the task. This can help you troubleshoot and identify any problems with your DAG or its tasks.
      - In the `Code` tab, you can see the code for that task, which can help you understand how the task is defined and executed. This can be useful for debugging and ensuring that your DAG is configured correctly.
      - In the `XCom` tab, you can see the XCom values for that task, which can help you understand the data being passed between tasks in your DAG. This can be useful for debugging and ensuring that your DAG is functioning as expected.      
      
      The other tabs (Rendered Template, Asset Events, Audit Log, Details) can also provide additional information about the task execution and can be useful for debugging and ensuring that your DAG is functioning as expected.

### Let us look at the Code of the tutorial DAG

- Let us look at the Code of the tutorial DAG, which is one of the example DAGs that come with Airflow. This DAG is a simple example that demonstrates how to use Airflow to run a few basic tasks, such as printing the date and sleeping for a few seconds. By examining the code of this DAG, you can understand how Airflow works and how to define your own DAGs for more complex workflows.

  - Note that the whole workflow of the **tutorial** DAG is defined in a single Python file. The DAG is defined using the Airflow SDK, which allows you to create and manage your DAGs programmatically. The tasks within this particular DAG are defined using the BashOperator, which allows you to execute bash commands as part of your workflow. By looking at the code of this DAG, you can see how to define tasks, set dependencies between tasks, and use Jinja templating to create dynamic commands.

  - **Operators** are the building blocks of Airflow DAGs. They define the individual **tasks** that make up your workflow. In the **tutorial** DAG, we use the BashOperator to execute simple bash commands. You can use other operators to perform different types of tasks, such as PythonOperator for executing Python code, or PostgresOperator for interacting with a PostgreSQL database. By understanding how to use operators, you can create complex workflows that automate various tasks in your data pipelines.

  - However, for `Destination Earth - Data Lake` related processing we imagine that **Python** based operators or **KubernetesPodOperator** will be more relevant for our use cases, as they allow us to run Python code and execute tasks in Kubernetes pods, which can be more suitable for data processing and machine learning workflows.

  - **PythonOperator** allows you to execute Python code directly within your DAG, which can be useful for tasks that involve data manipulation, machine learning, or any other Python-based processing. This operator is ideal for tasks that require more complex logic or integration with Python libraries.

  - **KubernetesPodOperator** allows you to run tasks in Kubernetes pods, which can be useful for tasks that require more resources or need to run in a specific environment. This operator is ideal for tasks that involve running containerized applications, such as data processing jobs or machine learning training tasks, in a Kubernetes cluster. By using **KubernetesPodOperator**, you can take advantage of the scalability and flexibility of Kubernetes to run your Airflow tasks efficiently.


Tutorial.py

```python

#
# Licensed to the Apache Software Foundation (ASF) under one
# ...

"""
### Tutorial Documentation
Documentation that goes along with the Airflow tutorial located
[here](https://airflow.apache.org/tutorial.html)
"""

from __future__ import annotations

# [START tutorial]
# [START import_module]
import textwrap
from datetime import datetime, timedelta

# Operators; we need this to operate!
from airflow.providers.standard.operators.bash import BashOperator

# The DAG object; we'll need this to instantiate a DAG
from airflow.sdk import DAG

# [END import_module]


# [START instantiate_dag]
with DAG(
    "tutorial",
    # [START default_args]
    # These args will get passed on to each operator
    # You can override them on a per-task basis during operator initialization
    default_args={
        "depends_on_past": False,
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
        # 'queue': 'bash_queue',
        # 'pool': 'backfill',
        # 'priority_weight': 10,
        # 'end_date': datetime(2016, 1, 1),
        # 'wait_for_downstream': False,
        # 'execution_timeout': timedelta(seconds=300),
        # 'on_failure_callback': some_function, # or list of functions
        # 'on_success_callback': some_other_function, # or list of functions
        # 'on_retry_callback': another_function, # or list of functions
        # 'sla_miss_callback': yet_another_function, # or list of functions
        # 'on_skipped_callback': another_function, #or list of functions
        # 'trigger_rule': 'all_success'
    },
    # [END default_args]
    description="A simple tutorial DAG",
    schedule=timedelta(days=1),
    start_date=datetime(2021, 1, 1),
    catchup=False,
    tags=["example"],
) as dag:
    # [END instantiate_dag]

    # t1, t2 and t3 are examples of tasks created by instantiating operators
    # [START basic_task]
    t1 = BashOperator(
        task_id="print_date",
        bash_command="date",
    )

    t2 = BashOperator(
        task_id="sleep",
        depends_on_past=False,
        bash_command="sleep 5",
        retries=3,
    )
    # [END basic_task]

    # [START documentation]
    t1.doc_md = textwrap.dedent(
        """\
    #### Task Documentation
    You can document your task using the attributes `doc_md` (markdown),
    `doc` (plain text), `doc_rst`, `doc_json`, `doc_yaml` which gets
    rendered in the UI's Task Instance Details page.
    ![img](https://imgs.xkcd.com/comics/fixing_problems.png)
    **Image Credit:** Randall Munroe, [XKCD](https://xkcd.com/license.html)
    """
    )

    dag.doc_md = __doc__  # providing that you have a docstring at the beginning of the DAG; OR
    dag.doc_md = """
    This is a documentation placed anywhere
    """  # otherwise, type it like this
    # [END documentation]

    # [START jinja_template]
    templated_command = textwrap.dedent(
        """
    {% for i in range(5) %}
        echo "{{ ds }}"
        echo "{{ macros.ds_add(ds, 7)}}"
    {% endfor %}
    """
    )

    t3 = BashOperator(
        task_id="templated",
        depends_on_past=False,
        bash_command=templated_command,
    )
    # [END jinja_template]

    t1 >> [t2, t3]
# [END tutorial]


```