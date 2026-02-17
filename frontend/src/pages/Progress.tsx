import ProgressCharts from '../features/progress/ProgressCharts';
import { pageCardStyle } from '../components/ui/pageCardStyle';

export default function Progress() {
  return (
    <main className="p-4 pb-24 space-y-4" style={{ backgroundColor: 'var(--pp-navy)', minHeight: '100vh' }}>
      <section className="p-4" style={pageCardStyle}>
        <h1 className="text-2xl font-bold text-text">Progress</h1>
        <p className="mt-2 text-sm text-muted">Daily and weekly trend surface for Home+Plate slice.</p>
      </section>
      <ProgressCharts />
    </main>
  );
}
