# Skill: Deploy to Cloud Run

## When to use
When I need to deploy the backend to Google Cloud Run.

## Steps

1. Make sure the app starts locally first:
```bash
uv run uvicorn src.main:app --port 8000 &
sleep 2
curl http://localhost:8000/health
kill %1
```

2. Deploy:
```bash
gcloud run deploy catchup-backend \
  --source . \
  --region europe-west1 \
  --min-instances 1 \
  --allow-unauthenticated \
  --set-env-vars "SUPABASE_URL=$SUPABASE_URL,SUPABASE_SERVICE_KEY=$SUPABASE_SERVICE_KEY,TAVILY_API_KEY=$TAVILY_API_KEY,GRADIUM_API_KEY=$GRADIUM_API_KEY,GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT,GOOGLE_CLOUD_LOCATION=$GOOGLE_CLOUD_LOCATION,LLM_API_KEY=$LLM_API_KEY,LLM_BASE_URL=$LLM_BASE_URL,LLM_MODEL=$LLM_MODEL"
```

3. Test the deployed version:
```bash
URL=$(gcloud run services describe catchup-backend --region europe-west1 --format 'value(status.url)')
curl $URL/health
```

## Notes
- min-instances=1 to avoid cold starts during demo
- Always test locally before deploying
- If deploy fails, check `gcloud run logs read catchup-backend --region europe-west1`
