import type { SetupFormValues } from "../schema";
import { describe, it, expect } from 'vitest';

export const mockValues: SetupFormValues = {
  sex: "female",
  age: 30,
  height_cm: 170,
  weight_kg: 65,
  activity: "moderate",
  goal: "maintain",
  diet_flags: [],
};

// Test suite to prevent "No test suite found" error
describe('test-utils.helper', () => {
  it('should export mock values', () => {
    expect(mockValues).toBeDefined();
    expect(mockValues.sex).toBe("female");
    expect(mockValues.age).toBe(30);
    expect(mockValues.height_cm).toBe(170);
    expect(mockValues.weight_kg).toBe(65);
    expect(mockValues.activity).toBe("moderate");
    expect(mockValues.goal).toBe("maintain");
    expect(Array.isArray(mockValues.diet_flags)).toBe(true);
  });
});
