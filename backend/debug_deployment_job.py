import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import Deployment, Job

async def check_deployment_job():
    async with AsyncSessionLocal() as db:
        # Find the deployment
        result = await db.execute(select(Deployment).where(Deployment.name == "tst-sagf-4235234232"))
        deployment = result.scalars().first()
        
        if not deployment:
            print("Deployment not found!")
            return
            
        print(f"Deployment Found: {deployment.id} (Name: {deployment.name})")
        
        # Find linked jobs
        result = await db.execute(select(Job).where(Job.deployment_id == deployment.id))
        jobs = result.scalars().all()
        
        print(f"Linked Jobs: {len(jobs)}")
        for job in jobs:
            print(f" - Job ID: {job.id}, Created At: {job.created_at}")

if __name__ == "__main__":
    asyncio.run(check_deployment_job())
