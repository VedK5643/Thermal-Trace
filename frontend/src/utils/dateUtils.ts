/**
 * India Standard Time (IST — Asia/Kolkata) Date Utilities for ThermalTrace.
 * Ensures all timeline calculations, date selection dropdowns, and status displays
 * operate strictly in IST rather than UTC zero-offset.
 */

/**
 * Returns today's calendar date in IST (Asia/Kolkata) formatted as YYYY-MM-DD.
 */
export function getTodayISTString(): string {
  const formatter = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kolkata' });
  return formatter.format(new Date());
}

/**
 * Returns YYYY-MM-DD in IST offset by a specified number of days relative to today.
 * e.g. daysOffset = 0 -> today IST, daysOffset = -1 -> yesterday IST.
 */
export function getISTDateOffset(daysOffset: number): string {
  const d = new Date();
  d.setDate(d.getDate() + daysOffset);
  const formatter = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kolkata' });
  return formatter.format(d);
}

/**
 * Formats a YYYY-MM-DD ISO string into human-readable IST format e.g. "27 Aug 2026".
 */
export function formatISTDateLabel(isoDate: string, includeYear: boolean = true): string {
  if (!isoDate) return '';
  const parts = isoDate.split('-');
  if (parts.length !== 3) return isoDate;

  const year = parseInt(parts[0], 10);
  const monthIdx = parseInt(parts[1], 10) - 1;
  const day = parseInt(parts[2], 10);

  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const monthName = months[monthIdx] || '';

  return includeYear ? `${day} ${monthName} ${year}` : `${day} ${monthName}`;
}

/**
 * Generates dynamic rolling list of past `numDays` dates ending on today IST.
 */
export function getRollingISTDates(numDays: number = 7): Array<{ label: string; isoDate: string; isToday: boolean }> {
  const todayIST = getTodayISTString();
  const dates = [];

  for (let i = numDays - 1; i >= 0; i--) {
    const isoDate = getISTDateOffset(-i);
    const label = formatISTDateLabel(isoDate, true);
    dates.push({
      label,
      isoDate,
      isToday: isoDate === todayIST,
    });
  }

  return dates;
}
