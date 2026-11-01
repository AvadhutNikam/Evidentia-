/**
 * Indian Forensics & Statutory Number / Date Formatters
 * Compliant with Indian Evidence Act / BSA & National Police Record standards:
 * - Date: DD/MM/YYYY with IST (Indian Standard Time)
 * - Currency: Indian Rupee Lakh/Crore grouping (e.g. ₹ 61,000 / ₹ 1,45,000 / ₹ 1.25 Crore)
 * - Numerals: Conversion between Western Arabic (123) and Devanagari (१२३)
 */

export const DEVANAGARI_DIGIT_MAP: Record<string, string> = {
  '0': '०', '1': '१', '2': '२', '3': '३', '4': '४',
  '5': '५', '6': '६', '7': '७', '8': '८', '9': '९'
};

export const WESTERN_DIGIT_MAP: Record<string, string> = {
  '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
  '५': '5', '६': '6', '७': '7', '८': '8', '९': '9'
};

/**
 * Converts Western digits to Devanagari digits.
 */
export function toDevanagariNumerals(value: string | number): string {
  const str = String(value);
  return str.replace(/[0-9]/g, (digit) => DEVANAGARI_DIGIT_MAP[digit] || digit);
}

/**
 * Converts Devanagari digits to Western digits.
 */
export function toWesternNumerals(value: string): string {
  return value.replace(/[०-९]/g, (digit) => WESTERN_DIGIT_MAP[digit] || digit);
}

/**
 * Formats a Date or ISO string to standard Indian police format: DD/MM/YYYY HH:mm IST
 */
export function formatIndianDate(
  dateInput: string | Date | null | undefined,
  includeTime: boolean = true,
  useDevanagari: boolean = false
): string {
  if (!dateInput) return '—';

  try {
    const d = typeof dateInput === 'string' ? new Date(dateInput) : dateInput;
    if (isNaN(d.getTime())) {
      // In case dateInput is already in DD/MM/YYYY text form
      return String(dateInput);
    }

    const day = String(d.getDate()).padStart(2, '0');
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const year = d.getFullYear();

    let formatted = `${day}/${month}/${year}`;

    if (includeTime) {
      const hours = String(d.getHours()).padStart(2, '0');
      const minutes = String(d.getMinutes()).padStart(2, '0');
      formatted += ` ${hours}:${minutes} IST`;
    }

    return useDevanagari ? toDevanagariNumerals(formatted) : formatted;
  } catch {
    return String(dateInput);
  }
}

/**
 * Formats monetary amounts in Indian Rupee format with Lakh and Crore commas:
 * e.g., 61000 -> ₹ 61,000
 * e.g., 1250000 -> ₹ 12,50,000
 * e.g., 10000000 -> ₹ 1,00,00,000
 */
export function formatIndianCurrency(
  amount: number | string | null | undefined,
  prefix: string = '₹ ',
  useDevanagari: boolean = false
): string {
  if (amount === null || amount === undefined || amount === '') return '—';

  const cleanNum = typeof amount === 'number' ? amount : parseFloat(String(amount).replace(/[^0-9.]/g, ''));
  if (isNaN(cleanNum)) return String(amount);

  // Format with Indian grouping (last 3 digits, then 2 digits each)
  const isNegative = cleanNum < 0;
  const absNum = Math.abs(cleanNum);
  const parts = absNum.toFixed(2).split('.');
  const integerPart = parts[0];
  const decimalPart = parts[1] === '00' ? '' : `.${parts[1]}`;

  let lastThree = integerPart.substring(integerPart.length - 3);
  const otherNumbers = integerPart.substring(0, integerPart.length - 3);
  if (otherNumbers !== '') {
    lastThree = ',' + lastThree;
  }
  const formattedInt = otherNumbers.replace(/\B(?=(\d{2})+(?!\d))/g, ',') + lastThree;
  const result = `${isNegative ? '-' : ''}${prefix}${formattedInt}${decimalPart}`;

  return useDevanagari ? toDevanagariNumerals(result) : result;
}

