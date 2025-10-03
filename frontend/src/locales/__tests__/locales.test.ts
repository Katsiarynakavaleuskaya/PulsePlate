import { describe, it, expect } from "vitest";
import en from "../en.json";
import es from "../es.json";
import ru from "../ru.json";

/**
 * Comprehensive locale validation tests
 * These tests ensure translation files are valid, complete, and consistent
 */

describe("Locale Files - JSON Structure", () => {
  it("should have valid JSON structure for en.json", () => {
    expect(en).toBeDefined();
    expect(typeof en).toBe("object");
    expect(en).not.toBeNull();
  });

  it("should have valid JSON structure for es.json", () => {
    expect(es).toBeDefined();
    expect(typeof es).toBe("object");
    expect(es).not.toBeNull();
  });

  it("should have valid JSON structure for ru.json", () => {
    expect(ru).toBeDefined();
    expect(typeof ru).toBe("object");
    expect(ru).not.toBeNull();
  });
});

describe("Locale Files - Key Completeness", () => {
  /**
   * Helper function to get all nested keys from an object
   */
  function getAllKeys(obj: Record<string, unknown>, prefix = ""): string[] {
    const keys: string[] = [];
    for (const key in obj) {
      const fullKey = prefix ? `${prefix}.${key}` : key;
      const value = obj[key];
      if (typeof value === "object" && value !== null && !Array.isArray(value)) {
        keys.push(...(getAllKeys(value as Record<string, unknown>, fullKey)));
      } else {
        keys.push(fullKey);
      }
    }
    return keys.sort();
  }

  it("should have all top-level sections in all locales", () => {
    const enSections = Object.keys(en);
    const esSections = Object.keys(es);
    const ruSections = Object.keys(ru);

    expect(esSections).toEqual(enSections);
    expect(ruSections).toEqual(enSections);
  });

  it("should have identical key structures across all locales", () => {
    const enKeys = getAllKeys(en as Record<string, unknown>);
    const esKeys = getAllKeys(es as Record<string, unknown>);
    const ruKeys = getAllKeys(ru as Record<string, unknown>);

    expect(esKeys).toEqual(enKeys);
    expect(ruKeys).toEqual(enKeys);
  });

  it("should have common section with required keys", () => {
    expect(en.common).toBeDefined();
    expect(en.common.ok).toBeDefined();
    expect(en.common.cancel).toBeDefined();

    expect(es.common).toBeDefined();
    expect(es.common.ok).toBeDefined();
    expect(es.common.cancel).toBeDefined();

    expect(ru.common).toBeDefined();
    expect(ru.common.ok).toBeDefined();
    expect(ru.common.cancel).toBeDefined();
  });

  it("should have shoplist section with required keys", () => {
    const requiredKeys = ["loading", "error", "empty"];
    
    requiredKeys.forEach(key => {
      expect(en.shoplist[key as keyof typeof en.shoplist]).toBeDefined();
      expect(es.shoplist[key as keyof typeof es.shoplist]).toBeDefined();
      expect(ru.shoplist[key as keyof typeof ru.shoplist]).toBeDefined();
    });
  });

  it("should have paywall section with all required keys", () => {
    const requiredTopKeys = ["title", "subtitle", "cta", "legal", "before", "after", "items"];
    
    requiredTopKeys.forEach(key => {
      expect(en.paywall[key as keyof typeof en.paywall]).toBeDefined();
      expect(es.paywall[key as keyof typeof es.paywall]).toBeDefined();
      expect(ru.paywall[key as keyof typeof ru.paywall]).toBeDefined();
    });
  });

  it("should have paywall.before section with required keys", () => {
    const requiredKeys = ["label", "randomPlate", "macrosOnly", "manualShopping"];
    
    requiredKeys.forEach(key => {
      expect(en.paywall.before[key as keyof typeof en.paywall.before]).toBeDefined();
      expect(es.paywall.before[key as keyof typeof es.paywall.before]).toBeDefined();
      expect(ru.paywall.before[key as keyof typeof ru.paywall.before]).toBeDefined();
    });
  });

  it("should have paywall.after section with required keys", () => {
    const requiredKeys = ["label", "personalPlate", "microBalance", "autoShoppingList"];
    
    requiredKeys.forEach(key => {
      expect(en.paywall.after[key as keyof typeof en.paywall.after]).toBeDefined();
      expect(es.paywall.after[key as keyof typeof es.paywall.after]).toBeDefined();
      expect(ru.paywall.after[key as keyof typeof ru.paywall.after]).toBeDefined();
    });
  });

  it("should have paywall.items.before section with required keys", () => {
    const requiredKeys = ["random_plate", "macros_only", "manual_shopping"];
    
    requiredKeys.forEach(key => {
      expect(en.paywall.items.before[key as keyof typeof en.paywall.items.before]).toBeDefined();
      expect(es.paywall.items.before[key as keyof typeof es.paywall.items.before]).toBeDefined();
      expect(ru.paywall.items.before[key as keyof typeof ru.paywall.items.before]).toBeDefined();
    });
  });

  it("should have paywall.items.after section with required keys", () => {
    const requiredKeys = ["personal_plate", "micro_balance", "auto_shopping_list"];
    
    requiredKeys.forEach(key => {
      expect(en.paywall.items.after[key as keyof typeof en.paywall.items.after]).toBeDefined();
      expect(es.paywall.items.after[key as keyof typeof es.paywall.items.after]).toBeDefined();
      expect(ru.paywall.items.after[key as keyof typeof ru.paywall.items.after]).toBeDefined();
    });
  });
});

describe("Locale Files - Translation Quality", () => {
  it("should have non-empty translations in Spanish", () => {
    const esKeys = [
      es.common.ok,
      es.common.cancel,
      es.shoplist.loading,
      es.shoplist.error,
      es.shoplist.empty,
      es.paywall.title,
      es.paywall.subtitle,
      es.paywall.cta,
      es.paywall.legal,
    ];

    esKeys.forEach(value => {
      expect(value).toBeTruthy();
      expect(value.length).toBeGreaterThan(0);
    });
  });

  it("should have non-empty translations in Russian", () => {
    const ruKeys = [
      ru.common.ok,
      ru.common.cancel,
      ru.shoplist.loading,
      ru.shoplist.error,
      ru.shoplist.empty,
      ru.paywall.title,
      ru.paywall.subtitle,
      ru.paywall.cta,
      ru.paywall.legal,
    ];

    ruKeys.forEach(value => {
      expect(value).toBeTruthy();
      expect(value.length).toBeGreaterThan(0);
    });
  });

  it("should have actual translations (not English) for Spanish paywall section", () => {
    // These should be different from English
    expect(es.paywall.title).not.toBe(en.paywall.title);
    expect(es.paywall.subtitle).not.toBe(en.paywall.subtitle);
    expect(es.paywall.cta).not.toBe(en.paywall.cta);
    expect(es.paywall.legal).not.toBe(en.paywall.legal);
  });

  it("should have actual translations (not English) for Russian paywall section", () => {
    // These should be different from English
    expect(ru.paywall.title).not.toBe(en.paywall.title);
    expect(ru.paywall.subtitle).not.toBe(en.paywall.subtitle);
    expect(ru.paywall.cta).not.toBe(en.paywall.cta);
    expect(ru.paywall.legal).not.toBe(en.paywall.legal);
  });

  it("should not have placeholder text or incomplete translations in Spanish", () => {
    const allSpanishValues = [
      es.common.ok,
      es.common.cancel,
      es.shoplist.loading,
      es.shoplist.error,
      es.shoplist.empty,
      es.paywall.title,
      es.paywall.subtitle,
      es.paywall.cta,
      es.paywall.legal,
      es.paywall.before.label,
      es.paywall.before.randomPlate,
      es.paywall.before.macrosOnly,
      es.paywall.before.manualShopping,
      es.paywall.after.label,
      es.paywall.after.personalPlate,
      es.paywall.after.microBalance,
      es.paywall.after.autoShoppingList,
    ];

    allSpanishValues.forEach(value => {
      expect(value).not.toMatch(new RegExp("TODO|FIXME|XXX|\\[.*\\]|\\.\\.\\.$"));
      expect(value.trim()).toBe(value); // No leading/trailing whitespace
    });
  });

  it("should not have placeholder text or incomplete translations in Russian", () => {
    const allRussianValues = [
      ru.common.ok,
      ru.common.cancel,
      ru.shoplist.loading,
      ru.shoplist.error,
      ru.shoplist.empty,
      ru.paywall.title,
      ru.paywall.subtitle,
      ru.paywall.cta,
      ru.paywall.legal,
      ru.paywall.before.label,
      ru.paywall.before.randomPlate,
      ru.paywall.before.macrosOnly,
      ru.paywall.before.manualShopping,
      ru.paywall.after.label,
      ru.paywall.after.personalPlate,
      ru.paywall.after.microBalance,
      ru.paywall.after.autoShoppingList,
    ];

    allRussianValues.forEach(value => {
      expect(value).not.toMatch(new RegExp("TODO|FIXME|XXX|\\[.*\\]"));
      expect(value.trim()).toBe(value); // No leading/trailing whitespace
    });
  });
});

describe("Locale Files - Spanish Translation Updates (Current Branch)", () => {
  it("should have updated shoplist.empty to 'Lista vacía.'", () => {
    expect(es.shoplist.empty).toBe("Lista vacía.");
  });

  it("should have improved paywall subtitle with detailed description", () => {
    expect(es.paywall.subtitle).toBe("Plan nutricional personalizado, equilibrio preciso, planificación semanal.");
    expect(es.paywall.subtitle).toContain("Plan nutricional personalizado");
    expect(es.paywall.subtitle).toContain("equilibrio preciso");
    expect(es.paywall.subtitle).toContain("planificación semanal");
  });

  it("should have updated legal text to reference 'Configuración' instead of 'Ajustes'", () => {
    expect(es.paywall.legal).toBe("Suscripción con renovación automática. Cancela en Configuración.");
    expect(es.paywall.legal).toContain("Configuración");
    expect(es.paywall.legal).not.toContain("Ajustes");
  });

  it("should have expanded 'macrosOnly' to 'Solo macronutrientes'", () => {
    expect(es.paywall.before.macrosOnly).toBe("Solo macronutrientes");
    expect(es.paywall.items.before.macros_only).toBe("Solo macronutrientes");
  });

  it("should have improved 'personalPlate' translation to 'Plan nutricional personalizado'", () => {
    expect(es.paywall.after.personalPlate).toBe("Plan nutricional personalizado");
    expect(es.paywall.items.after.personal_plate).toBe("Plan nutricional personalizado");
  });

  it("should have improved 'microBalance' translation to 'Equilibrio nutricional preciso'", () => {
    expect(es.paywall.after.microBalance).toBe("Equilibrio nutricional preciso");
    expect(es.paywall.items.after.micro_balance).toBe("Equilibrio nutricional preciso");
  });

  it("should have improved 'autoShoppingList' translation to 'Lista de compras automática'", () => {
    expect(es.paywall.after.autoShoppingList).toBe("Lista de compras automática");
    expect(es.paywall.items.after.auto_shopping_list).toBe("Lista de compras automática");
  });

  it("should maintain consistency between camelCase and snake_case keys in Spanish", () => {
    // Before section
    expect(es.paywall.before.randomPlate).toBe(es.paywall.items.before.random_plate);
    expect(es.paywall.before.macrosOnly).toBe(es.paywall.items.before.macros_only);
    expect(es.paywall.before.manualShopping).toBe(es.paywall.items.before.manual_shopping);

    // After section
    expect(es.paywall.after.personalPlate).toBe(es.paywall.items.after.personal_plate);
    expect(es.paywall.after.microBalance).toBe(es.paywall.items.after.micro_balance);
    expect(es.paywall.after.autoShoppingList).toBe(es.paywall.items.after.auto_shopping_list);
  });
});

describe("Locale Files - Russian Translation Updates (Current Branch)", () => {
  it("should have improved paywall subtitle with detailed description", () => {
    expect(ru.paywall.subtitle).toBe("Персональный план питания, точный баланс, недельная программа.");
    expect(ru.paywall.subtitle).toContain("Персональный план питания");
    expect(ru.paywall.subtitle).toContain("точный баланс");
    expect(ru.paywall.subtitle).toContain("недельная программа");
  });

  it("should have improved 'randomPlate' translation to 'Случайный рацион'", () => {
    expect(ru.paywall.before.randomPlate).toBe("Случайный рацион");
    expect(ru.paywall.items.before.random_plate).toBe("Случайный рацион");
    expect(ru.paywall.before.randomPlate).not.toContain("тарелка");
  });

  it("should have expanded 'macrosOnly' to 'Только макронутриенты'", () => {
    expect(ru.paywall.before.macrosOnly).toBe("Только макронутриенты");
    expect(ru.paywall.items.before.macros_only).toBe("Только макронутриенты");
  });

  it("should have improved 'personalPlate' translation to 'Персональный план питания'", () => {
    expect(ru.paywall.after.personalPlate).toBe("Персональный план питания");
    expect(ru.paywall.items.after.personal_plate).toBe("Персональный план питания");
  });

  it("should have improved 'microBalance' translation to 'Точный баланс питательных веществ'", () => {
    expect(ru.paywall.after.microBalance).toBe("Точный баланс питательных веществ");
    expect(ru.paywall.items.after.micro_balance).toBe("Точный баланс питательных веществ");
  });

  it("should have improved 'autoShoppingList' translation to 'Автоматический список покупок'", () => {
    expect(ru.paywall.after.autoShoppingList).toBe("Автоматический список покупок");
    expect(ru.paywall.items.after.auto_shopping_list).toBe("Автоматический список покупок");
  });

  it("should maintain consistency between camelCase and snake_case keys in Russian", () => {
    // Before section
    expect(ru.paywall.before.randomPlate).toBe(ru.paywall.items.before.random_plate);
    expect(ru.paywall.before.macrosOnly).toBe(ru.paywall.items.before.macros_only);
    expect(ru.paywall.before.manualShopping).toBe(ru.paywall.items.before.manual_shopping);

    // After section
    expect(ru.paywall.after.personalPlate).toBe(ru.paywall.items.after.personal_plate);
    expect(ru.paywall.after.microBalance).toBe(ru.paywall.items.after.micro_balance);
    expect(ru.paywall.after.autoShoppingList).toBe(ru.paywall.items.after.auto_shopping_list);
  });
});

describe("Locale Files - String Format Validation", () => {
  it("should have proper punctuation in Spanish shoplist.empty", () => {
    expect(es.shoplist.empty).toMatch(new RegExp("\\.$")); // Ends with period
  });

  it("should have proper punctuation in Spanish paywall.subtitle", () => {
    expect(es.paywall.subtitle).toMatch(new RegExp("\\.$")); // Ends with period
  });

  it("should have proper punctuation in Spanish paywall.legal", () => {
    expect(es.paywall.legal).toMatch(new RegExp("\\.$")); // Ends with period
  });

  it("should have proper punctuation in Russian paywall.subtitle", () => {
    expect(ru.paywall.subtitle).toMatch(new RegExp("\\.$")); // Ends with period
  });

  it("should have proper capitalization in Spanish translations", () => {
    expect(es.paywall.title.charAt(0)).toMatch(new RegExp("[A-ZА-Я]")); // Capital first letter
    expect(es.paywall.subtitle.charAt(0)).toMatch(new RegExp("[A-ZА-Я]"));
    expect(es.paywall.cta.charAt(0)).toMatch(new RegExp("[A-ZА-Я]"));
  });

  it("should have proper capitalization in Russian translations", () => {
    expect(ru.paywall.title.charAt(0)).toMatch(new RegExp("[A-ZА-Я]")); // Capital first letter
    expect(ru.paywall.subtitle.charAt(0)).toMatch(new RegExp("[A-ZА-Я]"));
    expect(ru.paywall.cta.charAt(0)).toMatch(new RegExp("[A-ZА-Я]"));
  });

  it("should not have double spaces in any Spanish translation", () => {
    const allSpanishValues = JSON.stringify(es);
    expect(allSpanishValues).not.toMatch(new RegExp("  +"));
  });

  it("should not have double spaces in any Russian translation", () => {
    const allRussianValues = JSON.stringify(ru);
    expect(allRussianValues).not.toMatch(new RegExp("  +"));
  });
});

describe("Locale Files - Edge Cases and Error Handling", () => {
  it("should handle empty string checks gracefully", () => {
    Object.values(en).forEach(section => {
      if (typeof section === "object" && section !== null) {
        Object.values(section).forEach(value => {
          if (typeof value === "string") {
            expect(value).not.toBe("");
          }
        });
      }
    });
  });

  it("should not have keys with undefined values in Spanish", () => {
    const checkUndefined = (obj: Record<string, unknown>) => {
      for (const key in obj) {
        const value = obj[key];
        if (typeof value === "object" && value !== null) {
          checkUndefined(value as Record<string, unknown>);
        } else {
          expect(value).toBeDefined();
        }
      }
    };

    checkUndefined(es as Record<string, unknown>);
  });

  it("should not have keys with undefined values in Russian", () => {
    const checkUndefined = (obj: Record<string, unknown>) => {
      for (const key in obj) {
        const value = obj[key];
        if (typeof value === "object" && value !== null) {
          checkUndefined(value as Record<string, unknown>);
        } else {
          expect(value).toBeDefined();
        }
      }
    };

    checkUndefined(ru as Record<string, unknown>);
  });

  it("should not have null values in any locale", () => {
    const checkNull = (obj: Record<string, unknown>) => {
      for (const key in obj) {
        const value = obj[key];
        expect(value).not.toBeNull();
        if (typeof value === "object" && value !== null) {
          checkNull(value as Record<string, unknown>);
        }
      }
    };

    checkNull(en as Record<string, unknown>);
    checkNull(es as Record<string, unknown>);
    checkNull(ru as Record<string, unknown>);
  });

  it("should have consistent nesting depth across all locales", () => {
    const getDepth = (obj: Record<string, unknown>, depth = 0): number => {
      if (typeof obj !== "object" || obj === null) return depth;
      return Math.max(
        depth,
        ...Object.values(obj).map(v =>
          getDepth(v as Record<string, unknown>, depth + 1)
        )
      );
    };

    const enDepth = getDepth(en as Record<string, unknown>);
    const esDepth = getDepth(es as Record<string, unknown>);
    const ruDepth = getDepth(ru as Record<string, unknown>);

    expect(esDepth).toBe(enDepth);
    expect(ruDepth).toBe(enDepth);
  });
});

describe("Locale Files - i18n Integration", () => {
  it("should be importable as modules", () => {
    expect(() => JSON.stringify(en)).not.toThrow();
    expect(() => JSON.stringify(es)).not.toThrow();
    expect(() => JSON.stringify(ru)).not.toThrow();
  });

  it("should have serializable content (no functions or symbols)", () => {
    const isSerializable = (obj: unknown): boolean => {
      if (obj === null || obj === undefined) return true;
      if (typeof obj === "function" || typeof obj === "symbol") return false;
      if (typeof obj === "object") {
        return Object.values(obj).every(isSerializable);
      }
      return true;
    };

    expect(isSerializable(en)).toBe(true);
    expect(isSerializable(es)).toBe(true);
    expect(isSerializable(ru)).toBe(true);
  });

  it("should maintain proper JSON structure after stringification and parsing", () => {
    const enParsed = JSON.parse(JSON.stringify(en));
    const esParsed = JSON.parse(JSON.stringify(es));
    const ruParsed = JSON.parse(JSON.stringify(ru));

    expect(enParsed).toEqual(en);
    expect(esParsed).toEqual(es);
    expect(ruParsed).toEqual(ru);
  });
});

describe("Locale Files - Regression Prevention", () => {
  it("should not revert Spanish translations back to old values", () => {
    // Ensure we don't accidentally revert to old translations
    expect(es.shoplist.empty).not.toBe("Vacío.");
    expect(es.paywall.legal).not.toContain("Ajustes");
    expect(es.paywall.before.macrosOnly).not.toBe("Solo macros");
    expect(es.paywall.after.personalPlate).not.toBe("Plato personal");
    expect(es.paywall.after.microBalance).not.toBe("Microequilibrio");
    expect(es.paywall.after.autoShoppingList).not.toBe("Lista automática");
  });

  it("should not revert Russian translations back to old values", () => {
    // Ensure we don't accidentally revert to old translations
    expect(ru.paywall.before.randomPlate).not.toBe("Случайная тарелка");
    expect(ru.paywall.before.macrosOnly).not.toBe("Только макро");
    expect(ru.paywall.after.personalPlate).not.toBe("Персональная тарелка");
    expect(ru.paywall.after.microBalance).not.toBe("Микро-баланс");
    expect(ru.paywall.after.autoShoppingList).not.toBe("Авто список покупок");
  });
});

describe("Locale Files - Translation Length Validation", () => {
  it("should have reasonable length translations (not too short or too long)", () => {
    // Paywall titles should be substantial but not excessive
    expect(es.paywall.title.length).toBeGreaterThan(5);
    expect(es.paywall.title.length).toBeLessThan(100);
    expect(ru.paywall.title.length).toBeGreaterThan(5);
    expect(ru.paywall.title.length).toBeLessThan(100);
  });

  it("should have comparable lengths between locales for the same key", () => {
    // Translations should be roughly comparable in length (within 3x)
    const checkLength = (enVal: string, otherVal: string, locale: string, key: string) => {
      const ratio = Math.max(enVal.length, otherVal.length) / Math.min(enVal.length, otherVal.length);
      expect(ratio).toBeLessThan(3);
    };

    checkLength(en.paywall.title, es.paywall.title, "es", "paywall.title");
    checkLength(en.paywall.title, ru.paywall.title, "ru", "paywall.title");
    checkLength(en.paywall.subtitle, es.paywall.subtitle, "es", "paywall.subtitle");
    checkLength(en.paywall.subtitle, ru.paywall.subtitle, "ru", "paywall.subtitle");
  });
});