// RU: Карточка с рекомендацией по потреблению воды
// EN: Card displaying water intake recommendation

interface WaterCardProps {
  liters: number;
}

export default function WaterCard({ liters }: WaterCardProps) {
  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm">
      <div className="flex items-center gap-4">
        <div className="flex-shrink-0">
          <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
            <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
            </svg>
          </div>
        </div>

        <div className="flex-1">
          <h3 className="text-lg font-semibold text-text">Вода</h3>
          <p className="text-muted text-sm mb-2">
            Рекомендуемое суточное потребление воды
          </p>
          <div className="text-2xl font-bold text-blue-600">
            {liters.toFixed(1)} л/день
          </div>
        </div>
      </div>

      <div className="mt-4 p-3 bg-blue-50 rounded-lg">
        <p className="text-xs text-blue-800">
          💡 <strong>Совет:</strong> Пейте воду равномерно в течение дня.
          Увеличивайте потребление при физической активности или жаркой погоде.
        </p>
      </div>
    </div>
  );
}
