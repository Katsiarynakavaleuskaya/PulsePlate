/** @vitest-environment node */
import { describe, test, expect } from "vitest";
import en from "../en.json";
import es from "../es.json";
import ru from "../ru.json";

/**
 * Comprehensive locale file validation tests
 * Tests structure consistency, key completeness, value types, and translation quality
 */

type LocaleStructure = Record<string, unknown>;

/**
 * Recursively extracts all translation keys from a locale object
 */
function extractKeys(obj: LocaleStructure, prefix = ""): Set<string> {
  const keys = new Set<string>();
  for (const [key, value] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${key}` : key;
    if (typeof value === "object" && value !== null && !Array.isArray(value)) {
      const nestedKeys = extractKeys(value as LocaleStructure, path);
      nestedKeys.forEach((k) => keys.add(k));
    } else {
      keys.add(path);
    }
  }
  return keys;
}

/**
 * Gets a value from a nested object using dot notation
 */
function getNestedValue(obj: LocaleStructure, path: string): unknown {
  return path.split(".").reduce((current: unknown, key: string) => {
    if (current && typeof current === "object" && key in (current as LocaleStructure)) {
      return (current as LocaleStructure)[key];
    }
    return undefined;
  }, obj);
}

/**
 * Validates that a value is a non-empty string
 */
function isValidTranslation(value: unknown): boolean {
  return typeof value === "string" && value.trim().length > 0;
}

describe("Locale Files - Structure Validation", () => {
  test("all locale files should be valid JSON objects", () => {
    expect(en).toBeTypeOf("object");
    expect(es).toBeTypeOf("object");
    expect(ru).toBeTypeOf("object");
  });

  test("all locale files should have the same top-level keys", () => {
    const enKeys = new Set(Object.keys(en));
    const esKeys = new Set(Object.keys(es));
    const ruKeys = new Set(Object.keys(ru));

    expect(esKeys).toEqual(enKeys);
    expect(ruKeys).toEqual(enKeys);
  });

  test("all locale files should have identical nested key structures", () => {
    const enKeys = extractKeys(en);
    const esKeys = extractKeys(es);
    const ruKeys = extractKeys(ru);

    expect(enKeys.size).toBeGreaterThan(0);
    expect(esKeys).toEqual(enKeys);
    expect(ruKeys).toEqual(enKeys);
  });

  test("all translation keys should have consistent depths across locales", () => {
    const enKeys = Array.from(extractKeys(en));

    enKeys.forEach((key) => {
      const enValue = getNestedValue(en, key);
      const esValue = getNestedValue(es, key);
      const ruValue = getNestedValue(ru, key);

      expect(typeof esValue).toBe(typeof enValue);
      expect(typeof ruValue).toBe(typeof enValue);
    });
  });
});

describe("Locale Files - Content Validation", () => {
  test("all translation values should be non-empty strings", () => {
    const allKeys = Array.from(extractKeys(en));

    allKeys.forEach((key) => {
      const enValue = getNestedValue(en, key);
      const esValue = getNestedValue(es, key);
      const ruValue = getNestedValue(ru, key);

      expect(isValidTranslation(enValue), `en.${key} should be a non-empty string`).toBe(true);
      expect(isValidTranslation(esValue), `es.${key} should be a non-empty string`).toBe(true);
      expect(isValidTranslation(ruValue), `ru.${key} should be a non-empty string`).toBe(true);
    });
  });

  test("no translation values should contain placeholder text", () => {
    const allKeys = Array.from(extractKeys(en));
    const placeholders = ["TODO", "FIXME", "XXX", "PLACEHOLDER"];

    allKeys.forEach((key) => {
      const esValue = getNestedValue(es, key) as string;
      const ruValue = getNestedValue(ru, key) as string;

      placeholders.forEach((placeholder) => {
        expect(esValue.toUpperCase()).not.toContain(placeholder);
        expect(ruValue.toUpperCase()).not.toContain(placeholder);
      });
    });
  });

  test("translation values should not be identical to English (except OK)", () => {
    const allKeys = Array.from(extractKeys(en)).filter((key) => !key.includes("common.ok"));

    allKeys.forEach((key) => {
      const enValue = getNestedValue(en, key) as string;
      const esValue = getNestedValue(es, key) as string;
      const ruValue = getNestedValue(ru, key) as string;

      // Spanish and Russian translations should differ from English
      expect(esValue, `es.${key} should not be identical to English`).not.toBe(enValue);
      expect(ruValue, `ru.${key} should not be identical to English`).not.toBe(enValue);
    });
  });
});

describe("Spanish Translations (es.json) - Updated Content", () => {
  test("common section should have correct Spanish translations", () => {
    expect(es.common.ok).toBe("OK");
    expect(es.common.cancel).toBe("Cancelar");
  });

  test("shoplist section should have correct Spanish translations", () => {
    expect(es.shoplist.loading).toBe("Cargando lista de compras…");
    expect(es.shoplist.error).toBe("Error");
    expect(es.shoplist.empty).toBe("Lista vacía.");
  });

  test("paywall section should have improved Spanish translations", () => {
    expect(es.paywall.title).toBe("Desbloquear Premium");
    expect(es.paywall.subtitle).toBe("Plan nutricional personal, equilibrio preciso, planificación semanal.");
    expect(es.paywall.cta).toBe("Continuar");
    expect(es.paywall.legal).toBe("Suscripción con renovación automática. Cancela en Configuración.");
  });

  test("paywall before section should have correct Spanish translations", () => {
    expect(es.paywall.before.label).toBe("Antes");
    expect(es.paywall.before.randomPlate).toBe("Plato aleatorio");
    expect(es.paywall.before.macrosOnly).toBe("Solo macronutrientes");
    expect(es.paywall.before.manualShopping).toBe("Lista manual");
  });

  test("paywall after section should have improved Spanish translations", () => {
    expect(es.paywall.after.label).toBe("Después");
    expect(es.paywall.after.personalPlate).toBe("Plan nutricional personal");
    expect(es.paywall.after.microBalance).toBe("Equilibrio nutricional");
    expect(es.paywall.after.autoShoppingList).toBe("Lista automática");
  });

  test("paywall items.before section should have correct Spanish translations", () => {
    expect(es.paywall.items.before.random_plate).toBe("Plato aleatorio");
    expect(es.paywall.items.before.macros_only).toBe("Solo macronutrientes");
    expect(es.paywall.items.before.manual_shopping).toBe("Lista manual");
  });

  test("paywall items.after section should have improved Spanish translations", () => {
    expect(es.paywall.items.after.personal_plate).toBe("Plan nutricional personal");
    expect(es.paywall.items.after.micro_balance).toBe("Equilibrio nutricional");
    expect(es.paywall.items.after.auto_shopping_list).toBe("Lista automática");
  });
});

describe("Russian Translations (ru.json) - Updated Content", () => {
  test("common section should have correct Russian translations", () => {
    expect(ru.common.ok).toBe("ОК");
    expect(ru.common.cancel).toBe("Отмена");
  });

  test("shoplist section should have correct Russian translations", () => {
    expect(ru.shoplist.loading).toBe("Загружаем список…");
    expect(ru.shoplist.error).toBe("Ошибка");
    expect(ru.shoplist.empty).toBe("Пусто.");
  });

  test("paywall section should have improved Russian translations", () => {
    expect(ru.paywall.title).toBe("Откройте Premium");
    expect(ru.paywall.subtitle).toBe("Персональный рацион, точный баланс, недельная программа.");
    expect(ru.paywall.cta).toBe("Продолжить");
    expect(ru.paywall.legal).toBe("Подписка продлевается автоматически. Отмена — в Настройках.");
  });

  test("paywall before section should have improved Russian translations", () => {
    expect(ru.paywall.before.label).toBe("До");
    expect(ru.paywall.before.randomPlate).toBe("Случайный рацион");
    expect(ru.paywall.before.macrosOnly).toBe("Только макронутриенты");
    expect(ru.paywall.before.manualShopping).toBe("Список покупок вручную");
  });

  test("paywall after section should have improved Russian translations", () => {
    expect(ru.paywall.after.label).toBe("После");
    expect(ru.paywall.after.personalPlate).toBe("Персональный рацион");
    expect(ru.paywall.after.microBalance).toBe("Точный баланс");
    expect(ru.paywall.after.autoShoppingList).toBe("Автосписок покупок");
  });

  test("paywall items.before section should have improved Russian translations", () => {
    expect(ru.paywall.items.before.random_plate).toBe("Случайный рацион");
    expect(ru.paywall.items.before.macros_only).toBe("Только макронутриенты");
    expect(ru.paywall.items.before.manual_shopping).toBe("Список покупок вручную");
  });

  test("paywall items.after section should have improved Russian translations", () => {
    expect(ru.paywall.items.after.personal_plate).toBe("Персональный рацион");
    expect(ru.paywall.items.after.micro_balance).toBe("Точный баланс");
    expect(ru.paywall.items.after.auto_shopping_list).toBe("Автосписок покупок");
  });
});

describe("Translation Quality - Spanish", () => {
  test("should use professional terminology for nutrition features", () => {
    // Verify improved translations use proper nutritional terminology
    expect(es.paywall.subtitle).toContain("nutricional");
    expect(es.paywall.after.personalPlate).toContain("Plan nutricional");
    expect(es.paywall.after.microBalance).toContain("Equilibrio nutricional");
    expect(es.paywall.before.macrosOnly).toContain("macronutrientes");
    expect(es.paywall.items.before.macros_only).toContain("macronutrientes");
  });

  test("should use consistent terminology across related keys", () => {
    // "Plan nutricional personal" should be consistent
    expect(es.paywall.after.personalPlate).toBe("Plan nutricional personal");
    expect(es.paywall.items.after.personal_plate).toBe("Plan nutricional personal");

    // "Equilibrio nutricional" should be consistent
    expect(es.paywall.after.microBalance).toBe("Equilibrio nutricional");
    expect(es.paywall.items.after.micro_balance).toBe("Equilibrio nutricional");
  });

  test("should use appropriate formal tone", () => {
    expect(es.paywall.legal).toContain("Configuración");
    expect(es.paywall.legal).not.toContain("Ajustes");
  });
});

describe("Translation Quality - Russian", () => {
  test("should use professional terminology for nutrition features", () => {
    // Verify improved translations use proper terminology
    expect(ru.paywall.subtitle).toContain("рацион");
    expect(ru.paywall.after.personalPlate).toContain("рацион");
    expect(ru.paywall.after.microBalance).toContain("баланс");
    expect(ru.paywall.before.macrosOnly).toContain("макронутриенты");
  });

  test("should use consistent terminology across related keys", () => {
    // "Персональный рацион" should be consistent
    expect(ru.paywall.after.personalPlate).toBe("Персональный рацион");
    expect(ru.paywall.items.after.personal_plate).toBe("Персональный рацион");

    // "Точный баланс" should be consistent
    expect(ru.paywall.after.microBalance).toBe("Точный баланс");
    expect(ru.paywall.items.after.micro_balance).toBe("Точный баланс");

    // "Случайный рацион" should be consistent
    expect(ru.paywall.before.randomPlate).toBe("Случайный рацион");
    expect(ru.paywall.items.before.random_plate).toBe("Случайный рацион");
  });

  test("should avoid hyphenated compound words where appropriate", () => {
    // Updated translations should not use "микро-баланс"
    expect(ru.paywall.after.microBalance).not.toContain("микро-");
    expect(ru.paywall.items.after.micro_balance).not.toContain("микро-");
  });

  test("should use natural Russian phrasing", () => {
    // "Автосписок" instead of "Авто список"
    expect(ru.paywall.after.autoShoppingList).toBe("Автосписок покупок");
    expect(ru.paywall.items.after.auto_shopping_list).toBe("Автосписок покупок");
  });
});

describe("Special Characters and Formatting", () => {
  test("ellipsis should be properly formatted", () => {
    expect(es.shoplist.loading).toContain("…");
    expect(ru.shoplist.loading).toContain("…");
  });

  test("periods should be used consistently for empty states", () => {
    expect(es.shoplist.empty).toMatch(/\.$/);
    expect(ru.shoplist.empty).toMatch(/\.$/);
  });

  test("should not have trailing or leading whitespace", () => {
    const allKeys = Array.from(extractKeys(en));

    allKeys.forEach((key) => {
      const esValue = getNestedValue(es, key) as string;
      const ruValue = getNestedValue(ru, key) as string;

      expect(esValue).toBe(esValue.trim());
      expect(ruValue).toBe(ruValue.trim());
    });
  });

  test("should use proper punctuation marks", () => {
    // Russian em dash in legal text
    expect(ru.paywall.legal).toContain("—");

    // Spanish and Russian should use proper punctuation
    expect(es.paywall.legal).toMatch(/\.$/);
    expect(ru.paywall.legal).toMatch(/\.$/);
  });
});

describe("Locale File Integrity", () => {
  test("should not contain duplicate keys at any level", () => {
    const checkDuplicates = (obj: LocaleStructure, path = ""): void => {
      const keys = Object.keys(obj);
      const uniqueKeys = new Set(keys);
      expect(uniqueKeys.size, `Duplicate keys found at ${path || "root"}`).toBe(keys.length);

      keys.forEach((key) => {
        const value = obj[key];
        if (typeof value === "object" && value !== null && !Array.isArray(value)) {
          checkDuplicates(value as LocaleStructure, path ? `${path}.${key}` : key);
        }
      });
    };

    checkDuplicates(es);
    checkDuplicates(ru);
  });

  test("JSON files should be properly formatted", () => {
    // Verify files can be stringified and parsed
    expect(() => JSON.stringify(es)).not.toThrow();
    expect(() => JSON.stringify(ru)).not.toThrow();
    expect(() => JSON.parse(JSON.stringify(es))).not.toThrow();
    expect(() => JSON.parse(JSON.stringify(ru))).not.toThrow();
  });
});

describe("Regression Tests - Previous Issues", () => {
  test("Spanish should not use old abbreviated terminology", () => {
    // Ensure old translations are replaced
    const esStr = JSON.stringify(es);
    expect(esStr).not.toContain("Solo macros");
    expect(esStr).not.toContain("Ajustes"); // Should use "Configuración"
    expect(esStr).not.toContain("Plato personal"); // Should use "Plan nutricional personal"
    expect(esStr).not.toContain("Microequilibrio");
  });

  test("Russian should not use old compound word forms", () => {
    const ruStr = JSON.stringify(ru);
    expect(ruStr).not.toContain("Персональная тарелка");
    expect(ruStr).not.toContain("Случайная тарелка");
    expect(ruStr).not.toContain("микро-баланс");
    expect(ruStr).not.toContain("Только макро");
  });

  test("should maintain backwards compatibility with i18n key structure", () => {
    // Ensure structure hasn't changed
    expect(es.paywall.items.before).toBeDefined();
    expect(es.paywall.items.after).toBeDefined();
    expect(ru.paywall.items.before).toBeDefined();
    expect(ru.paywall.items.after).toBeDefined();
  });
});

describe("Translation Completeness Edge Cases", () => {
  test("should handle nested object traversal correctly", () => {
    expect(es.paywall.items.before.random_plate).toBeTruthy();
    expect(ru.paywall.items.after.micro_balance).toBeTruthy();
  });

  test("all leaf nodes should be strings, not objects", () => {
    const checkLeafNodes = (obj: LocaleStructure, path = ""): void => {
      Object.entries(obj).forEach(([key, value]) => {
        const currentPath = path ? `${path}.${key}` : key;
        if (typeof value === "object" && value !== null) {
          // Should have nested keys
          expect(Object.keys(value as LocaleStructure).length).toBeGreaterThan(0);
          checkLeafNodes(value as LocaleStructure, currentPath);
        } else {
          // Leaf node should be a string
          expect(typeof value, `${currentPath} should be a string`).toBe("string");
        }
      });
    };

    checkLeafNodes(es);
    checkLeafNodes(ru);
  });
});