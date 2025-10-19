import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar
} from 'recharts';
import { Download, TrendingUp, TrendingDown } from 'lucide-react';

// Mock data for progress tracking
const weightData = [
  { date: '2024-01-01', weight: 75.2, bmi: 24.1 },
  { date: '2024-01-08', weight: 74.8, bmi: 23.9 },
  { date: '2024-01-15', weight: 74.3, bmi: 23.7 },
  { date: '2024-01-22', weight: 73.9, bmi: 23.6 },
  { date: '2024-01-29', weight: 73.5, bmi: 23.4 },
  { date: '2024-02-05', weight: 73.2, bmi: 23.3 },
  { date: '2024-02-12', weight: 72.8, bmi: 23.1 },
];

const calorieData = [
  { date: '2024-01-01', consumed: 2100, burned: 1800, net: 300 },
  { date: '2024-01-08', consumed: 2050, burned: 1850, net: 200 },
  { date: '2024-01-15', consumed: 2000, burned: 1900, net: 100 },
  { date: '2024-01-22', consumed: 1950, burned: 1950, net: 0 },
  { date: '2024-01-29', consumed: 1900, burned: 2000, net: -100 },
  { date: '2024-02-05', consumed: 1850, burned: 2050, net: -200 },
  { date: '2024-02-12', consumed: 1800, burned: 2100, net: -300 },
];

const macroData = [
  { name: 'Protein', value: 120, color: '#8884d8', percentage: 25 },
  { name: 'Carbs', value: 180, color: '#82ca9d', percentage: 37 },
  { name: 'Fat', value: 80, color: '#ffc658', percentage: 17 },
  { name: 'Fiber', value: 30, color: '#ff7300', percentage: 6 },
  { name: 'Other', value: 70, color: '#00ff88', percentage: 15 },
];

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
};

const exportToPDF = async () => {
  // Simple PDF export using html2canvas + jspdf
  try {
    const html2canvas = await import('html2canvas');
    const { jsPDF } = await import('jspdf');
    const element = document.getElementById('progress-charts');
    if (element) {
      const canvas = await html2canvas.default(element, {
        scale: 2,
        useCORS: true,
        allowTaint: true,
      });
      const imgData = canvas.toDataURL('image/png');
      const pdf = new jsPDF('p', 'mm', 'a4');
      const imgWidth = 210;
      const pageHeight = 295;
      const imgHeight = (canvas.height * imgWidth) / canvas.width;
      let heightLeft = imgHeight;

      let position = 0;

      pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
      heightLeft -= pageHeight;

      while (heightLeft >= 0) {
        position = heightLeft - imgHeight;
        pdf.addPage();
        pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
        heightLeft -= pageHeight;
      }

      pdf.save('progress-report.pdf');
    }
  } catch (error) {
    console.error('Failed to export PDF:', error);
  }
};

export default function ProgressCharts() {
  const latestWeight = weightData[weightData.length - 1];
  const previousWeight = weightData[weightData.length - 2];
  const weightChange = latestWeight.weight - previousWeight.weight;
  const isWeightLoss = weightChange < 0;

  return (
    <div id="progress-charts" className="space-y-6 p-4">
      {/* Header with Export Button */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold" style={{ color: 'var(--pp-text)' }}>Progress Tracking</h2>
          <p style={{ color: 'var(--pp-muted)' }}>Monitor your health journey</p>
        </div>
        <button
          onClick={exportToPDF}
          className="flex items-center gap-2 px-4 py-2 rounded-lg transition-colors hover:opacity-90"
          style={{
            backgroundColor: 'var(--pp-primary)',
            color: 'var(--pp-text)'
          }}
        >
          <Download className="w-4 h-4" />
          Export PDF
        </button>
      </div>

      {/* Weight Progress Chart */}
      <div
        className="rounded-lg p-6 shadow-sm"
        style={{
          backgroundColor: 'rgba(255, 255, 255, 0.1)',
          border: '1px solid rgba(255, 255, 255, 0.1)'
        }}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold" style={{ color: 'var(--pp-text)' }}>Weight & BMI Progress</h3>
          <div className="flex items-center gap-2">
            {isWeightLoss ? (
              <TrendingDown className="w-5 h-5" style={{ color: 'var(--pp-accent)' }} />
            ) : (
              <TrendingUp className="w-5 h-5" style={{ color: '#ff6b6b' }} />
            )}
            <span
              className="text-sm font-medium"
              style={{ color: isWeightLoss ? 'var(--pp-accent)' : '#ff6b6b' }}
            >
              {Math.abs(weightChange).toFixed(1)} kg {isWeightLoss ? 'lost' : 'gained'}
            </span>
          </div>
        </div>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={weightData}>
            <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
            <XAxis
              dataKey="date"
              tickFormatter={formatDate}
              className="text-gray-600 dark:text-gray-400"
            />
            <YAxis className="text-gray-600 dark:text-gray-400" />
            <Tooltip
              labelFormatter={(value) => formatDate(value)}
              contentStyle={{
                backgroundColor: 'rgba(255, 255, 255, 0.95)',
                border: 'none',
                borderRadius: '8px',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
              }}
            />
            <Line
              type="monotone"
              dataKey="weight"
              stroke="#3b82f6"
              strokeWidth={3}
              dot={{ fill: '#3b82f6', strokeWidth: 2, r: 4 }}
              name="Weight (kg)"
            />
            <Line
              type="monotone"
              dataKey="bmi"
              stroke="#10b981"
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={{ fill: '#10b981', strokeWidth: 2, r: 3 }}
              name="BMI"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Calorie Balance Chart */}
      <div
        className="rounded-lg p-6 shadow-sm"
        style={{
          backgroundColor: 'rgba(255, 255, 255, 0.1)',
          border: '1px solid rgba(255, 255, 255, 0.1)'
        }}
      >
        <h3 className="text-lg font-semibold mb-4" style={{ color: 'var(--pp-text)' }}>Calorie Balance</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={calorieData}>
            <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
            <XAxis
              dataKey="date"
              tickFormatter={formatDate}
              className="text-gray-600 dark:text-gray-400"
            />
            <YAxis className="text-gray-600 dark:text-gray-400" />
            <Tooltip
              labelFormatter={(value) => formatDate(value)}
              contentStyle={{
                backgroundColor: 'rgba(255, 255, 255, 0.95)',
                border: 'none',
                borderRadius: '8px',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
              }}
            />
            <Bar dataKey="consumed" fill="#ef4444" name="Consumed" />
            <Bar dataKey="burned" fill="#10b981" name="Burned" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Macronutrient Distribution */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div
          className="rounded-lg p-6 shadow-sm"
          style={{
            backgroundColor: 'rgba(255, 255, 255, 0.1)',
            border: '1px solid rgba(255, 255, 255, 0.1)'
          }}
        >
          <h3 className="text-lg font-semibold mb-4" style={{ color: 'var(--pp-text)' }}>Macronutrient Distribution</h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={macroData}
                cx="50%"
                cy="50%"
                outerRadius={80}
                dataKey="value"
                label={({ name, percentage }) => `${name}: ${percentage}%`}
              >
                {macroData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: 'rgba(255, 255, 255, 0.95)',
                  border: 'none',
                  borderRadius: '8px',
                  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div
          className="rounded-lg p-6 shadow-sm"
          style={{
            backgroundColor: 'rgba(255, 255, 255, 0.1)',
            border: '1px solid rgba(255, 255, 255, 0.1)'
          }}
        >
          <h3 className="text-lg font-semibold mb-4" style={{ color: 'var(--pp-text)' }}>Nutrient Breakdown</h3>
          <div className="space-y-3">
            {macroData.map((nutrient, index) => (
              <div key={index} className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div
                    className="w-4 h-4 rounded"
                    style={{ backgroundColor: nutrient.color }}
                  />
                  <span style={{ color: 'var(--pp-text)' }}>{nutrient.name}</span>
                </div>
                <div className="text-right">
                  <div style={{ color: 'var(--pp-text)' }} className="font-medium">{nutrient.value}g</div>
                  <div style={{ color: 'var(--pp-muted)' }} className="text-sm">{nutrient.percentage}%</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
