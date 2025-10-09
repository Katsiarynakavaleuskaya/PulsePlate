import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';

/**
 * MSW Server for Premium API Endpoints
 *
 * This server provides robust mocks for premium endpoints with comprehensive error handling.
 * Each endpoint includes:
 * - Request payload validation
 * - 400 Bad Request responses for invalid inputs
 * - 500 Internal Server Error responses for testing retries/fallbacks
 * - Success responses matching the expected API schema
 */

// Types for request validation
interface BmrRequest {
  weight_kg: number;
  height_cm: number;
  age: number;
  sex: string;
  activity: string;
  bodyfat?: number | null;
  lang?: string;
}

interface PlateRequest {
  sex: string;
  age: number;
  height_cm: number;
  weight_kg: number;
  activity: string;
  goal: string;
  deficit_pct?: number | null;
  surplus_pct?: number | null;
  bodyfat?: number | null;
  diet_flags?: string[] | null;
}

interface TargetsRequest {
  sex: string;
  age: number;
  height_cm: number;
  weight_kg: number;
  activity: string;
  goal?: string;
  deficit_pct?: number | null;
  surplus_pct?: number | null;
  bodyfat?: number | null;
  diet_flags?: string[] | null;
  life_stage?: string;
  lang?: string;
}

// Request validation helpers
function validateBmrRequest(req: BmrRequest): { isValid: boolean; error?: string } {
  if (req.weight_kg == null) {
    return { isValid: false, error: 'weight_kg is required' };
  }
  if (req.weight_kg <= 0) {
    return { isValid: false, error: 'weight_kg must be > 0' };
  }
  if (req.height_cm == null) {
    return { isValid: false, error: 'height_cm is required' };
  }
  if (req.height_cm <= 0) {
    return { isValid: false, error: 'height_cm must be > 0' };
  }
  if (req.age === undefined || req.age < 0 || req.age > 120) {
    return { isValid: false, error: 'age must be 0-120' };
  }
  if (!['male', 'female'].includes(req.sex)) {
    return { isValid: false, error: 'sex must be male or female' };
  }
  if (!['sedentary', 'light', 'moderate', 'active', 'very_active'].includes(req.activity)) {
    return { isValid: false, error: 'activity must be one of: sedentary, light, moderate, active, very_active' };
  }
  if (req.bodyfat !== undefined && req.bodyfat !== null && (req.bodyfat < 0 || req.bodyfat > 60)) {
    return { isValid: false, error: 'bodyfat must be 0-60' };
  }
  return { isValid: true };
}

function validatePlateRequest(req: PlateRequest): { isValid: boolean; error?: string } {
  if (!['male', 'female'].includes(req.sex)) {
    return { isValid: false, error: 'sex must be male or female' };
  }
  if (req.age === undefined || !Number.isFinite(req.age) || req.age < 10 || req.age > 100) {
    return { isValid: false, error: 'age must be 10-100' };
  }
  if (req.height_cm == null) {
    return { isValid: false, error: 'height_cm is required' };
  }
  if (req.height_cm <= 0) {
    return { isValid: false, error: 'height_cm must be > 0' };
  }
  if (req.weight_kg == null) {
    return { isValid: false, error: 'weight_kg is required' };
  }
  if (req.weight_kg <= 0) {
    return { isValid: false, error: 'weight_kg must be > 0' };
  }
  if (!['sedentary', 'light', 'moderate', 'active', 'very_active'].includes(req.activity)) {
    return { isValid: false, error: 'activity must be one of: sedentary, light, moderate, active, very_active' };
  }
  if (!['loss', 'maintain', 'gain'].includes(req.goal)) {
    return { isValid: false, error: 'goal must be loss, maintain, or gain' };
  }
  if (req.deficit_pct !== undefined && req.deficit_pct !== null && (req.deficit_pct < 5 || req.deficit_pct > 25)) {
    return { isValid: false, error: 'deficit_pct must be 5-25' };
  }
  if (req.surplus_pct !== undefined && req.surplus_pct !== null && (req.surplus_pct < 5 || req.surplus_pct > 20)) {
    return { isValid: false, error: 'surplus_pct must be 5-20' };
  }
  if (req.bodyfat !== undefined && req.bodyfat !== null && (req.bodyfat < 3 || req.bodyfat > 60)) {
    return { isValid: false, error: 'bodyfat must be 3-60' };
  }
  return { isValid: true };
}

function validateTargetsRequest(req: TargetsRequest): { isValid: boolean; error?: string } {
  if (!['male', 'female'].includes(req.sex)) {
    return { isValid: false, error: 'sex must be male or female' };
  }
  if (req.age === undefined || !Number.isFinite(req.age) || req.age < 1 || req.age > 120) {
    return { isValid: false, error: 'age must be 1-120' };
  }
  if (req.height_cm == null) {
    return { isValid: false, error: 'height_cm is required' };
  }
  if (req.height_cm <= 0) {
    return { isValid: false, error: 'height_cm must be > 0' };
  }
  if (req.weight_kg == null) {
    return { isValid: false, error: 'weight_kg is required' };
  }
  if (req.weight_kg <= 0) {
    return { isValid: false, error: 'weight_kg must be > 0' };
  }
  if (!['sedentary', 'light', 'moderate', 'active', 'very_active'].includes(req.activity)) {
    return { isValid: false, error: 'activity must be one of: sedentary, light, moderate, active, very_active' };
  }
  if (req.goal && !['loss', 'maintain', 'gain'].includes(req.goal)) {
    return { isValid: false, error: 'goal must be loss, maintain, or gain' };
  }
  if (req.deficit_pct !== undefined && req.deficit_pct !== null && (req.deficit_pct < 5 || req.deficit_pct > 25)) {
    return { isValid: false, error: 'deficit_pct must be 5-25' };
  }
  if (req.surplus_pct !== undefined && req.surplus_pct !== null && (req.surplus_pct < 5 || req.surplus_pct > 20)) {
    return { isValid: false, error: 'surplus_pct must be 5-20' };
  }
  if (req.bodyfat !== undefined && req.bodyfat !== null && (req.bodyfat < 3 || req.bodyfat > 60)) {
    return { isValid: false, error: 'bodyfat must be 3-60' };
  }
  if (req.life_stage && !['child', 'teen', 'adult', 'pregnant', 'lactating', 'elderly'].includes(req.life_stage)) {
    return { isValid: false, error: 'life_stage must be one of: child, teen, adult, pregnant, lactating, elderly' };
  }
  return { isValid: true };
}

export const handlers = [
  // BMR Endpoint - /api/v1/premium/bmr
  // Schema: BMRRequest (app.py:573) -> BMRResponse (app.py:585)
  // Required fields: weight_kg (>0), height_cm (>0), age (0-120), sex (male/female), activity
  // Optional: bodyfat (0-60), lang
  http.post('/api/v1/premium/bmr', async ({ request }) => {
    try {
      const req = await request.json() as BmrRequest;
      const validation = validateBmrRequest(req);

      // Simulate server error for testing retries/fallbacks
      if (req.weight_kg === 999) {
        return HttpResponse.json(
          { error: 'Internal server error' },
          { status: 500 }
        );
      }

      // Return 400 for invalid requests
      if (!validation.isValid) {
        return HttpResponse.json(
          { error: validation.error },
          { status: 400 }
        );
      }

      // Success response matching BMRResponse schema
      return HttpResponse.json({
        bmr: { mifflin: 1500, harris: 1480, katch: req.bodyfat ? 1520 : undefined },
        tdee: { mifflin: 2100, harris: 2080, katch: req.bodyfat ? 2120 : undefined },
        activity_level: `${req.activity} activity`,
        recommended_intake: {
          maintenance: 2100,
          weight_loss: 1680,
          weight_gain: 2310
        },
        formulas_used: req.bodyfat ? ['mifflin', 'harris', 'katch'] : ['mifflin', 'harris'],
        notes: req.bodyfat ? ['Katch-McArdle formula used for body fat percentage'] : []
      });
    } catch {
      // Handle JSON parsing errors
      return HttpResponse.json(
        { error: 'Invalid JSON payload' },
        { status: 400 }
      );
    }
  }),

  // Plate Endpoint - /api/v1/premium/plate
  // Schema: PlateRequest (app.py:1204) -> PlateResponse (app.py:1235)
  // Required fields: sex, age (10-100), height_cm (>0), weight_kg (>0), activity, goal
  // Optional: deficit_pct (5-25), surplus_pct (5-20), bodyfat (3-60), diet_flags
  http.post('/api/v1/premium/plate', async ({ request }) => {
    try {
      const req = await request.json() as PlateRequest;
      const validation = validatePlateRequest(req);

      // Simulate server error for testing retries/fallbacks
      if (req.age === 999) {
        return HttpResponse.json(
          { error: 'Internal server error' },
          { status: 500 }
        );
      }

      // Return 400 for invalid requests
      if (!validation.isValid) {
        return HttpResponse.json(
          { error: validation.error },
          { status: 400 }
        );
      }

      // Success response matching PlateResponse schema
      const baseKcal = req.goal === 'loss' ? 1800 : req.goal === 'gain' ? 2400 : 2100;
      return HttpResponse.json({
        kcal: baseKcal,
        macros: {
          protein_g: 131,
          fat_g: 70,
          carbs_g: 236,
          fiber_g: 30
        },
        portions: {
          protein_palm: 4.0,
          carb_cups: 8.0,
          veg_cups: 3.0,
          fat_thumbs: 2.5
        },
        layout: [
          { kind: 'plate_sector', fraction: 0.35, label: 'Protein', tooltip: 'Lean protein sources' },
          { kind: 'plate_sector', fraction: 0.40, label: 'Carbs', tooltip: 'Whole grains and vegetables' },
          { kind: 'plate_sector', fraction: 0.20, label: 'Vegetables', tooltip: 'Non-starchy vegetables' },
          { kind: 'plate_sector', fraction: 0.05, label: 'Fats', tooltip: 'Healthy fats' }
        ],
        meals: [
          {
            title: 'Breakfast',
            kcal: Math.round(baseKcal * 0.3),
            protein_g: Math.round(131 * 0.3),
            fat_g: Math.round(70 * 0.3),
            carbs_g: Math.round(236 * 0.3),
            micros: {
              iron_mg: 2.5,
              calcium_mg: 150,
              magnesium_mg: 45
            }
          },
          {
            title: 'Lunch',
            kcal: Math.round(baseKcal * 0.4),
            protein_g: Math.round(131 * 0.4),
            fat_g: Math.round(70 * 0.4),
            carbs_g: Math.round(236 * 0.4),
            micros: {
              iron_mg: 2.5,
              calcium_mg: 150,
              magnesium_mg: 45
            }
          },
          {
            title: 'Dinner',
            kcal: Math.round(baseKcal * 0.3),
            // Use subtraction to absorb rounding errors from breakfast/lunch
            protein_g: 131 - Math.round(131 * 0.7),
            fat_g: 70 - Math.round(70 * 0.7),
            carbs_g: 236 - Math.round(236 * 0.7),
            micros: {
              iron_mg: 2.5,
              calcium_mg: 150,
              magnesium_mg: 45
            }
          }
        ],
        day_micros: {
          iron_mg: 7.5,
          calcium_mg: 450,
          magnesium_mg: 135
        }
      });
    } catch {
      // Handle JSON parsing errors
      return HttpResponse.json(
        { error: 'Invalid JSON payload' },
        { status: 400 }
      );
    }
  }),

  // Targets Endpoint - /api/v1/premium/targets
  // Schema: WHOTargetsRequest (app.py:1247) -> WHOTargetsResponse (app.py:1937+)
  // Required fields: sex, age (1-120), height_cm (>0), weight_kg (>0), activity
  // Optional: goal, deficit_pct (5-25), surplus_pct (5-20), bodyfat (3-60), diet_flags, life_stage, lang
  http.post('/api/v1/premium/targets', async ({ request }) => {
    try {
      const req = await request.json() as TargetsRequest;
      const validation = validateTargetsRequest(req);

      // Simulate server error for testing retries/fallbacks
      if (req.height_cm === 999) {
        return HttpResponse.json(
          { error: 'Internal server error' },
          { status: 500 }
        );
      }

      // Return 400 for invalid requests
      if (!validation.isValid) {
        return HttpResponse.json(
          { error: validation.error },
          { status: 400 }
        );
      }

      // Success response matching WHOTargetsResponse schema
      const baseKcal = (req.goal === 'loss') ? 1800 : (req.goal === 'gain') ? 2400 : 2100;
      return HttpResponse.json({
        kcal_daily: baseKcal,
        macros: {
          protein_g: 131,
          fat_g: 70,
          carbs_g: 236,
          fiber_g: 30
        },
        water_ml: 2500,
        priority_micros: {
          iron_mg: req.sex === 'male' ? 8 : 18,
          calcium_mg: 1000,
          vitamin_c_mg: req.sex === 'male' ? 90 : 75,
          folate_ug: 400,
          vitamin_d_iu: 600,
          magnesium_mg: 400,
          potassium_mg: 3500,
          b12_ug: 2.4
        },
        activity_weekly: {
          moderate_aerobic_min: 150,
          vigorous_aerobic_min: 75,
          strength_sessions: 2,
          steps_daily: 8000
        },
        calculation_date: new Date().toISOString().split('T')[0],
        warnings: req.life_stage === 'pregnant' ? [{
          code: 'life_stage',
          message: 'Special nutrition considerations apply for pregnancy'
        }] : []
      });
    } catch {
      // Handle JSON parsing errors
      return HttpResponse.json(
        { error: 'Invalid JSON payload' },
        { status: 400 }
      );
    }
  }),
];

export const server = setupServer(...handlers);
