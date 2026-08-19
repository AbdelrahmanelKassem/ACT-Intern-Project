def create_chunks(raw_text: str, chunk_size: int = 50, overlap: int = 10):
    words = raw_text.split()

    chunks = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)

        start += chunk_size - overlap

    return chunks


text = """
Hotel check-in starts at 3 PM.
Hotel check-out is at 11 AM.

The hotel has a swimming pool.
The swimming pool is open from 7 AM to 10 PM.

Breakfast is served from 7 AM to 10 AM.
"""

chunks = create_chunks(text, chunk_size=10, overlap=2)

print("Number of chunks:", len(chunks))

for i, chunk in enumerate(chunks):
    print(f"\n--- Chunk {i + 1} ---")
    print(chunk)