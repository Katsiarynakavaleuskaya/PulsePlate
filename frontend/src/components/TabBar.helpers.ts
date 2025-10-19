/**
 * TabBar helper functions
 *
 * Utility functions for TabBar component logic
 */

/**
 * Maps tab count to Tailwind CSS grid classes
 * @param count Number of visible tabs (1-6)
 * @returns Tailwind grid class string
 */
export const getGridColsClass = (count: number): string => {
  switch (count) {
    case 1:
      return 'grid-cols-1';
    case 2:
      return 'grid-cols-2';
    case 3:
      return 'grid-cols-3';
    case 4:
      return 'grid-cols-4';
    case 5:
      return 'grid-cols-5';
    case 6:
      return 'grid-cols-6';
    default:
      return 'grid-cols-3';
  }
};
