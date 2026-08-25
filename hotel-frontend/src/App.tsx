import Chatbot from "./components/Chatbot";

function App() {
  return (
    <main className="min-h-screen bg-white text-neutral-900 font-sans">
      <section className="h-[70vh] bg-neutral-100 flex flex-col justify-center px-12 md:px-24 border-b border-gray-200">
        <h1 className="text-6xl md:text-8xl font-bold tracking-tighter mb-6">
          THE <br/> GRAND <br/> HOTEL.
        </h1>
        <p className="max-w-md text-lg text-neutral-600 leading-relaxed">
          Experience uncompromising luxury and meticulous design in the heart of the city. 
        </p>
      </section>

      <section className="py-20 px-12 md:px-24">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="col-span-1 md:col-span-2 bg-neutral-50 p-10 border border-gray-200">
            <h2 className="text-3xl font-semibold tracking-tight mb-4">Our Suites</h2>
            <p className="text-neutral-600 mb-8 max-w-lg">
              Carefully curated spaces featuring bespoke furniture and panoramic views. Designed for maximum comfort and minimal distraction.
            </p>
            <button className="bg-neutral-900 text-white px-6 py-3 text-sm font-medium hover:bg-neutral-800 transition">
              Explore Rooms
            </button>
          </div>
          <div className="col-span-1 bg-neutral-900 text-white p-10 flex flex-col justify-between">
            <div>
              <h2 className="text-2xl font-semibold tracking-tight mb-2">Dining</h2>
              <p className="text-neutral-400 text-sm">Michelin-starred culinary experiences await.</p>
            </div>
            <button className="text-left text-sm uppercase tracking-widest border-b border-white pb-1 w-max mt-12 hover:text-gray-300">
              Reserve a Table
            </button>
          </div>
        </div>
      </section>

      {/* This line mounts your chatbot to the page */}
      <Chatbot />
    </main>
  );
}

export default App;