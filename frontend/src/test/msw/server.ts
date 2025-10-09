import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';

// пример моков — подправь под свои эндпойнты
export const handlers = [
  http.post('/api/v1/premium/bmr', async () => {
    return HttpResponse.json({ bmr: 1500, tdee: 2100, method: 'mifflin' });
  }),
  http.post('/api/v1/premium/plate', async () => {
    return HttpResponse.json({
      plate: { carbs_pct: 45, protein_pct: 25, fat_pct: 30, kcal: 2100 },
      macros: { carbs_g: 236, protein_g: 131, fat_g: 70, fiber_g: 30 },
      water_l: 2.5,
    });
  }),
  http.get('/api/v1/premium/targets', async () => {
    return HttpResponse.json({
      micros: [
        { id: 'iron', name: 'Iron', unit: 'mg', target: 18 },
        { id: 'calcium', name: 'Calcium', unit: 'mg', target: 1000 },
      ],
    });
  }),
];

export const server = setupServer(...handlers);
