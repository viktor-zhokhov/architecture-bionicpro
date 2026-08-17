import React, { useState } from 'react';
import { useKeycloak } from '@react-keycloak/web';

interface ReportEntry {
  device_id: string;
  total_sessions: number;
  total_movements: number;
  avg_response_time_ms: number;
  avg_signal_quality: number;
  avg_battery_level: number;
  last_activity: string;
  report_date: string;
}

interface ReportResponse {
  user_id: string;
  username: string;
  report: ReportEntry[];
}

const ReportPage: React.FC = () => {
  const { keycloak, initialized } = useKeycloak();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<ReportResponse | null>(null);

  const downloadReport = async () => {
    if (!keycloak?.token) {
      setError('Not authenticated');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${process.env.REACT_APP_API_URL}/reports`, {
        headers: {
          'Authorization': `Bearer ${keycloak.token}`
        }
      });

      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail || `Error ${response.status}`);
      }

      const data: ReportResponse = await response.json();
      setReport(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  if (!initialized) {
    return <div>Loading...</div>;
  }

  if (!keycloak.authenticated) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
        <button
          onClick={() => keycloak.login()}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          Login
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
      <div className="p-8 bg-white rounded-lg shadow-md w-full max-w-4xl">
        <h1 className="text-2xl font-bold mb-6">Usage Reports</h1>

        <button
          onClick={downloadReport}
          disabled={loading}
          className={`px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 ${
            loading ? 'opacity-50 cursor-not-allowed' : ''
          }`}
        >
          {loading ? 'Generating Report...' : 'Download Report'}
        </button>

        {error && (
          <div className="mt-4 p-4 bg-red-100 text-red-700 rounded">
            {error}
          </div>
        )}

        {report && report.report.length > 0 && (
          <div className="mt-6">
            <h2 className="text-lg font-semibold mb-3">
              Report for {report.username}
            </h2>
            <table className="w-full border-collapse border border-gray-300">
              <thead>
                <tr className="bg-gray-50">
                  <th className="border border-gray-300 px-3 py-2 text-left">Device</th>
                  <th className="border border-gray-300 px-3 py-2 text-right">Sessions</th>
                  <th className="border border-gray-300 px-3 py-2 text-right">Movements</th>
                  <th className="border border-gray-300 px-3 py-2 text-right">Avg Response (ms)</th>
                  <th className="border border-gray-300 px-3 py-2 text-right">Signal Quality</th>
                  <th className="border border-gray-300 px-3 py-2 text-right">Battery</th>
                  <th className="border border-gray-300 px-3 py-2 text-left">Last Activity</th>
                </tr>
              </thead>
              <tbody>
                {report.report.map((entry, idx) => (
                  <tr key={idx}>
                    <td className="border border-gray-300 px-3 py-2">{entry.device_id}</td>
                    <td className="border border-gray-300 px-3 py-2 text-right">{entry.total_sessions}</td>
                    <td className="border border-gray-300 px-3 py-2 text-right">{entry.total_movements}</td>
                    <td className="border border-gray-300 px-3 py-2 text-right">{entry.avg_response_time_ms}</td>
                    <td className="border border-gray-300 px-3 py-2 text-right">{entry.avg_signal_quality.toFixed(1)}%</td>
                    <td className="border border-gray-300 px-3 py-2 text-right">{entry.avg_battery_level.toFixed(1)}%</td>
                    <td className="border border-gray-300 px-3 py-2">{entry.last_activity}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {report && report.report.length === 0 && (
          <div className="mt-4 p-4 bg-yellow-100 text-yellow-700 rounded">
            No report data available yet.
          </div>
        )}
      </div>
    </div>
  );
};

export default ReportPage;
