import { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { MessageSquare, BarChart3, AlertCircle, Star } from 'lucide-react';

interface IntentData {
  intent: string;
  count: number;
}

export default function AnalyticsDashboard() {
  const [topIntents, setTopIntents] = useState<IntentData[]>([]);
  const [totalMessages, setTotalMessages] = useState<number>(0);
  const [averageRating, setAverageRating] = useState<number | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const HOTEL_ID = "19a70845-1b5e-423a-b5c6-83a9851bbebe";
  const API_BASE_URL = "http://127.0.0.1:8000";

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        setLoading(true);
        
        const [intentsResponse, volumeResponse, ratingResponse] = await Promise.all([
          fetch(`${API_BASE_URL}/analytics/${HOTEL_ID}/top-intents`),
          fetch(`${API_BASE_URL}/analytics/${HOTEL_ID}/message-volume`),
          fetch(`${API_BASE_URL}/analytics/${HOTEL_ID}/average-rating`)
        ]);

        if (!intentsResponse.ok || !volumeResponse.ok || !ratingResponse.ok) {
          throw new Error("Failed to fetch dashboard data");
        }

        const intentsData = await intentsResponse.json();
        const volumeData = await volumeResponse.json();
        const ratingData = await ratingResponse.json();

        setTopIntents(intentsData);
        setTotalMessages(volumeData.total_inbound_messages);
        setAverageRating(ratingData.average_rating);
        setError(null);
      } catch (err) {
        console.error(err);
        setError("Failed to load analytics data. Make sure your FastAPI backend is running.");
      } finally {
        setLoading(false);
      }
    };

    fetchAnalytics();
  }, []);

  if (loading) {
    return <div style={{ padding: '2rem', textAlign: 'center' }}>Loading dashboard data...</div>;
  }

  if (error) {
    return (
      <div style={{ padding: '2rem', color: 'red', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <AlertCircle /> {error}
      </div>
    );
  }

  return (
    <div style={{ padding: '2rem', fontFamily: 'system-ui, sans-serif', maxWidth: '1000px', margin: '0 auto' }}>
      <h1 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '2rem' }}>
        <BarChart3 />
        Hotel Chatbot Analytics
      </h1>

      {/* KPI Cards Container */}
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem' }}>
        <div style={{ 
          padding: '1.5rem', 
          border: '1px solid #e5e7eb', 
          borderRadius: '8px', 
          boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
          flex: 1
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#6b7280', marginBottom: '0.5rem' }}>
            <MessageSquare size={20} />
            <h3 style={{ margin: 0, fontSize: '1rem' }}>Total Inbound Messages</h3>
          </div>
          <p style={{ fontSize: '2.5rem', fontWeight: 'bold', margin: 0 }}>{totalMessages}</p>
        </div>

        {/* NEW: Average Rating Card */}
        <div style={{ 
          padding: '1.5rem', 
          border: '1px solid #e5e7eb', 
          borderRadius: '8px', 
          boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
          flex: 1
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#6b7280', marginBottom: '0.5rem' }}>
            <Star size={20} className="text-yellow-500 fill-yellow-500" />
            <h3 style={{ margin: 0, fontSize: '1rem' }}>Average CSAT Score</h3>
          </div>
          <p style={{ fontSize: '2.5rem', fontWeight: 'bold', margin: 0 }}>
            {averageRating ? averageRating.toFixed(1) : "0.0"} <span style={{ fontSize: '1rem', color: '#6b7280', fontWeight: 'normal' }}>/ 5.0</span>
          </p>
        </div>
      </div>

      {/* Chart Container */}
      <div style={{ 
        padding: '1.5rem', 
        border: '1px solid #e5e7eb', 
        borderRadius: '8px', 
        boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
      }}>
        <h3 style={{ margin: '0 0 1.5rem 0', color: '#374151' }}>Top Guest Intents</h3>
        <div style={{ height: '400px', width: '100%' }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={topIntents} layout="vertical" margin={{ top: 5, right: 30, left: 40, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" />
              <YAxis dataKey="intent" type="category" width={120} tick={{ fontSize: 12 }} />
              <Tooltip cursor={{ fill: '#f3f4f6' }} />
              <Bar dataKey="count" fill="#3b82f6" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}