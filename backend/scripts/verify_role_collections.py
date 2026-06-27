import os
import sys
import asyncio

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.retrieval.hybrid_search import search

async def test_search(query: str, role: str):
    print(f"\nQuerying: '{query}' as Role: '{role}'")
    results = await search(query, role)
    if not results:
        print("  -> [NO RESULTS FOUND]")
    else:
        for idx, doc in enumerate(results):
            print(f"  -> Match {idx+1}: {doc['source']} (Score: {doc['score']:.4f})")
            print(f"     Content snippet: {doc['content'].strip()}")

async def main():
    await test_search("RMA hardware process must be initiated within 14 days", "support")
    await test_search("Standard discount limit is 15%", "support")
    await test_search("Standard discount limit is 15%", "sales")
    await test_search("RMA hardware process must be initiated within 14 days", "sales")
    await test_search("Q3 department expansion budget", "manager")
    await test_search("database backup rotation", "manager")
    await test_search("database backup rotation", "admin")

if __name__ == "__main__":
    asyncio.run(main())