// RU: Сетка с целями по микроэлементам
// EN: Grid displaying micronutrient targets

interface MicroItem {
  id: string;
  name: string;
  unit: string;
  target: number;
}

interface MicrosGridProps {
  items?: MicroItem[];
}

export default function MicrosGrid({ items }: MicrosGridProps) {
  if (!items || items.length === 0) {
    return (
      <div className="text-center py-8 text-muted">
        <p>Цели по микроэлементам недоступны</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
      {items.map((item) => (
        <div
          key={item.id}
          className="bg-white rounded-xl p-3 border border-muted/30 hover:shadow-sm transition-shadow"
        >
          <div className="text-sm font-medium text-text mb-1">{item.name}</div>
          <div className="text-lg font-bold text-primary">
            {item.target} <span className="text-sm font-normal text-muted">{item.unit}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
