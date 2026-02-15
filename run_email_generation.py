import asyncio
from src.enrichment.email_generator import EmailGenerator

async def main():
    generator = EmailGenerator()
    await generator.process_contacts()

if __name__ == "__main__":
    asyncio.run(main())
