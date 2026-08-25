import asyncio
import uuid
from sqlalchemy import select
from database import AsyncSessionLocal
from models import Chain, Hotel, Guest, SessionContext, KnowledgeBase, Document, ChunkingTable
from services.ai_factory import get_dynamic_embeddings

async def seed_database():
    async with AsyncSessionLocal() as session:
        try:
            # 1. Check if hotels already exist
            result = await session.execute(select(Hotel))
            existing_hotels = result.scalars().all()

            if not existing_hotels:
                marriott_id = uuid.uuid4()
                kempinski_id = uuid.uuid4()

                marriott = Chain(id=marriott_id, name="Marriott International")
                kempinski = Chain(id=kempinski_id, name="Kempinski Hotels")
                session.add_all([marriott, kempinski])

                hotels = [
                    Hotel(
                        id=uuid.uuid4(),
                        chain_id=marriott_id,
                        name="Cairo Marriott Hotel & Omar Khayyam Casino",
                        location="Zamalek, Cairo, Egypt",
                        widget_api_key="widget_marriott_zmalek_991"
                    ),
                    Hotel(
                        id=uuid.uuid4(),
                        chain_id=marriott_id,
                        name="JW Marriott Hotel Cairo",
                        location="New Cairo, Cairo, Egypt",
                        widget_api_key="widget_marriott_newcairo_992"
                    ),
                    Hotel(
                        id=uuid.uuid4(),
                        chain_id=marriott_id,
                        name="The Nile Ritz-Carlton, Cairo",
                        location="Tahrir Square, Cairo, Egypt",
                        widget_api_key="widget_marriott_ritz_993"
                    ),
                    Hotel(
                        id=uuid.uuid4(),
                        chain_id=marriott_id,
                        name="Sheraton Cairo Hotel & Casino",
                        location="Dokki, Giza, Egypt",
                        widget_api_key="widget_marriott_sheraton_994"
                    )
                ]
                session.add_all(hotels)
                await session.flush()
                target_hotel = hotels[0]
            else:
                target_hotel = existing_hotels[0]

            # 2. Create a fresh Guest
            test_guest_id = uuid.uuid4()
            test_guest = Guest(
                id=test_guest_id,
                name="Test Guest",
                phone="+1234567890",
                email="guest@test.com"
            )
            session.add(test_guest)

            # 3. Create a fresh SessionContext linked to the valid hotel
            test_session_id = uuid.uuid4()
            test_session = SessionContext(
                id=test_session_id,
                hotel_id=target_hotel.id,
                guest_id=test_guest_id,
                status="active"
            )
            session.add(test_session)

            # Flush guest and session context
            await session.flush()

            # 4. Feed the AI: Create Knowledge Base, Document & Vector Embeddings
            kb_result = await session.execute(select(KnowledgeBase).where(KnowledgeBase.hotel_id == target_hotel.id))
            existing_kb = kb_result.scalars().first()

            if not existing_kb:
                print("Generating vector embedding for the Knowledge Base using Gemini...")
                
                kb_id = uuid.uuid4()
                kb = KnowledgeBase(id=kb_id, hotel_id=target_hotel.id, name="General Hotel Info")
                session.add(kb)
                await session.flush()
                
                doc_id = uuid.uuid4()
                doc = Document(id=doc_id, knowledge_base_id=kb_id, title="Hotel Overview", source_type="text")
                session.add(doc)
                await session.flush()

                # Flush KB and Document so their IDs exist in PostgreSQL before inserting the chunk
                await session.flush()

                chunk_text = f"Welcome to the {target_hotel.name}. We are a luxury hotel located in {target_hotel.location}. We feature beautifully appointed rooms, a world-class casino, and excellent dining options."
                
                embeddings_model = get_dynamic_embeddings()
                vector = embeddings_model.embed_query(chunk_text)

                chunk = ChunkingTable(
                    id=uuid.uuid4(),
                    document_id=doc_id,
                    content_text=chunk_text,
                    vector_embedding=vector
                )
                session.add(chunk)
                await session.flush()
                print("Knowledge Base created and embedded successfully!")

            # 5. Commit all changes
            await session.commit()
            print("\n" + "=" * 60)
            print("Successfully verified hotels, generated RAG data, and created a new session!")
            print(f"USE THIS SESSION ID: {test_session_id}")
            print(f"HOTEL LINKED: {target_hotel.name} ({target_hotel.id})")
            print("=" * 60 + "\n")

        except Exception as e:
            await session.rollback()
            print(f"An error occurred while seeding: {e}")

if __name__ == "__main__":
    asyncio.run(seed_database())