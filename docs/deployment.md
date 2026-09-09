# Deployment Guide

## Local Development

### Docker Compose

```bash
cp .env.example .env
make docker-up
```

### Manual

```bash
make install
make api          # Terminal 1
make dashboard    # Terminal 2
```

---

## Cloud Deployment (AWS)

### Architecture

```text
GitHub Actions
    │
    ├── Docker build → ECR
    └── Terraform → AWS resources
           │
    ┌──────┼──────┐
    │      │      │
   ECR   S3    RDS
    │      │      │
    ▼      ▼      ▼
  ECS   Models  Data
    │
┌───┴────┐
│        │
API   Dashboard
```

### Prerequisites

1. AWS account with appropriate permissions
2. GitHub repository with OIDC configured
3. Terraform state S3 bucket (created manually once)

### One-Time Setup

#### 1. Create GitHub OIDC Provider in AWS

```bash
# Create IAM OIDC provider for GitHub Actions
aws iam create-open-id-connect-provider \
  --url "https://token.actions.githubusercontent.com" \
  --thumbprint-list "6938fd4d98bab03faadb97b34396831e3780aea1" \
  --client-id-list "sts.amazonaws.com"
```

#### 2. Create Deployment IAM Role

Create an IAM role that GitHub Actions can assume:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
      },
      "StringLike": {
        "token.actions.githubusercontent.com:sub": "repo:OWNER/fraudlens:*"
      }
    }
  }]
}
```

Attach policies:
- `AmazonEC2ContainerRegistryFullAccess` (for ECR)
- Custom policy for ECS deployment
- Custom policy for S3 read access

#### 3. Create Terraform State Bucket (once)

```bash
aws s3 mb s3://fraudlens-terraform-state --region us-east-1
aws dynamodb create-table \
  --table-name fraudlens-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

#### 4. Set GitHub Secrets

```text
AWS_ACCOUNT_ID          — AWS account ID
AWS_DEPLOYMENT_ROLE_ARN — IAM role ARN for deployment
AWS_TERRAFORM_ROLE_ARN  — IAM role ARN for Terraform
```

### Deploy Infrastructure

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with real values

terraform init
terraform plan
terraform apply
```

### Deploy Application

Push to `main` branch triggers:

1. Tests pass
2. Docker images built
3. Images pushed to ECR
4. ECS services updated
5. Health check verified

### Upload Model to S3

```bash
# Train model locally
python -c "
from fraudlens.models.serving import train_and_persist_model
import pandas as pd
df = pd.read_csv('path/to/data.csv')  # or use training data
train_and_persist_model(df, output_dir='models/')
"

# Upload to S3
aws s3 cp models/random_forest.artifact.pkl \
  s3://fraudlens-prod-artifacts/models/random_forest/v001/model.pkl
```

### Upload Dataset to S3 (one-time)

```bash
aws s3 cp data/raw/V1-nigerian-financial-transactions-and-fraud-detection-dataset.csv \
  s3://fraudlens-prod-artifacts/datasets/v1/
```

### Teardown

```bash
cd terraform
terraform destroy
```

---

## Environment Variables

| Variable | Local | Cloud |
| --- | --- | --- |
| `DATABASE_URL` | localhost | RDS endpoint |
| `FRAUDLENS_MODEL_PATH` | local file | S3 URI |
| `FRAUDLENS_LOG_LEVEL` | INFO | INFO |

---

## Cost Estimate

| Service | Monthly Cost (est.) |
| --- | --- |
| RDS db.t3.micro | ~$15 |
| ECS Fargate (2 tasks, 0.25 vCPU) | ~$15 |
| ALB | ~$5 |
| S3 | ~$1 |
| CloudWatch | ~$1 |
| ECR | ~$1 |
| **Total** | **~$38/month** |
