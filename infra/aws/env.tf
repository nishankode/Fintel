locals {
  database_url = "postgresql+psycopg://${var.database_username}:${var.database_password}@${aws_db_instance.postgres.address}:5432/${var.database_name}"
  redis_url    = "redis://${aws_elasticache_cluster.redis.cache_nodes[0].address}:6379/0"

  api_environment = [
    {
      name  = "APP_NAME"
      value = "Fintel"
    },
    {
      name  = "APP_VERSION"
      value = var.app_version
    },
    {
      name  = "ENVIRONMENT"
      value = var.environment
    },
    {
      name  = "DEBUG"
      value = "false"
    },
    {
      name  = "SEC_USER_AGENT"
      value = var.sec_user_agent
    },
    {
      name  = "DOCUMENT_STORAGE_PROVIDER"
      value = "s3"
    },
    {
      name  = "S3_BUCKET_NAME"
      value = aws_s3_bucket.filings.bucket
    },
    {
      name  = "S3_KEY_PREFIX"
      value = "raw"
    },
    {
      name  = "S3_REGION_NAME"
      value = var.aws_region
    },
    {
      name  = "EMBEDDING_MODEL_NAME"
      value = "BAAI/bge-small-en-v1.5"
    },
    {
      name  = "EMBEDDING_DIMENSION"
      value = "384"
    },
    {
      name  = "EMBEDDING_DEVICE"
      value = "cpu"
    },
    {
      name  = "REDIS_URL"
      value = local.redis_url
    },
    {
      name  = "INGESTION_QUEUE_NAME"
      value = "fintel:ingestion_jobs"
    },
    {
      name  = "LLM_PROVIDER"
      value = var.llm_provider
    },
    {
      name  = "OPENAI_MODEL"
      value = var.openai_model
    }
  ]

  api_secrets = [
    {
      name      = "DATABASE_URL"
      valueFrom = aws_secretsmanager_secret.database_url.arn
    },
    {
      name      = "JWT_SECRET_KEY"
      valueFrom = aws_secretsmanager_secret.jwt_secret_key.arn
    },
    {
      name      = "OPENAI_API_KEY"
      valueFrom = aws_secretsmanager_secret.openai_api_key.arn
    }
  ]
}
