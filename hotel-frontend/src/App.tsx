import { useState } from "react";
import Chatbot from "./components/Chatbot";
import AnalyticsDashboard from "./components/AnalyticsDashboard";
import { LayoutDashboard, Hotel } from "lucide-react";

function App() {
  const [activeTab, setActiveTab] = useState<"guest" | "analytics">("guest");

  return (
    <div className="min-h-screen bg-white text-neutral-900 font-sans flex flex-col">
      {/* Top Navigation Bar */}
      <header className="flex items-center justify-between px-8 py-4 border-b border-gray-200 bg-white/90 backdrop-blur sticky top-0 z-40">
        <div className="flex items-center gap-3">
          <span className="font-bold tracking-wider text-sm uppercase">
            The Grand Hotel & Resorts
          </span>
        </div>

        {/* View Switcher */}
        <div className="flex items-center bg-neutral-100 p-1 rounded-lg border border-gray-200 text-xs font-medium">
          <button
            onClick={() => setActiveTab("guest")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md transition ${
              activeTab === "guest"
                ? "bg-white text-neutral-900 shadow-sm"
                : "text-neutral-500 hover:text-neutral-900"
            }`}
          >
            <Hotel size={14} />
            Guest View
          </button>
          <button
            onClick={() => setActiveTab("analytics")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md transition ${
              activeTab === "analytics"
                ? "bg-white text-neutral-900 shadow-sm"
                : "text-neutral-500 hover:text-neutral-900"
            }`}
          >
            <LayoutDashboard size={14} />
            Manager Analytics
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      {activeTab === "guest" ? (
        <main>
          {/* Hero Section */}
          <section className="h-[70vh] bg-neutral-100 flex flex-col justify-center px-12 md:px-24 border-b border-gray-200">
            <h1 className="text-6xl md:text-8xl font-bold tracking-tighter mb-6">
              THE <br /> GRAND <br /> HOTEL.
            </h1>
            <p className="max-w-md text-lg text-neutral-600 leading-relaxed">
              Experience uncompromising luxury and meticulous design in the heart of the city.
            </p>
          </section>

          {/* Hotel Features Section */}
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

          {/* Chatbot widget mounted for guests */}
          <Chatbot />
        </main>
      ) : (
        <main className="flex-1 bg-neutral-50 py-10 px-6">
          <AnalyticsDashboard />
        </main>
      )}
    </div>
  );
}

export default App;