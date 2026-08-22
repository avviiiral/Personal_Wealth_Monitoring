import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
  ChangeDetectorRef,
  Component,
  ElementRef,
  HostListener,
  OnInit,
  inject,
} from '@angular/core';
import type ExcelJS from 'exceljs';

import {
  PortfolioApiService,
  FamilyNode,
  Transaction,
} from '../../core/services/portfolio-api.service';

/* ==============================================================
   REPORTS TREE
   Family
      Sub Class
         Underlying
            Transactions
   ============================================================== */

interface UnderlyingGroup {
  underlying: string;
  transactions: Transaction[];
}

interface SubClassGroup {
  sub_class: string;
  underlyings: UnderlyingGroup[];
  transaction_count: number;
}

interface FamilyGroup {
  family_name: string;
  sub_classes: SubClassGroup[];
  transaction_count: number;
}

/* Aggregate row used only by the Summary View download. */
interface SubClassSummaryRow {
  family_name: string;
  sub_class: string;
  quantity: number;
  invested_value: number;
  current_value: number;
  gain: number;
  xirr: number | null;
}

const UNASSIGNED = 'Unassigned';

@Component({
  selector: 'app-reports',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './reports.component.html',
  styleUrl: './reports.component.scss',
})
export class ReportsComponent implements OnInit {
  private readonly portfolioApi = inject(PortfolioApiService);
  private readonly cdr = inject(ChangeDetectorRef);
  private readonly elementRef = inject(ElementRef);

  families: FamilyGroup[] = [];

  /* Kept only to build the Summary View download (Family -> Sub
     Class aggregated quantity/invested/current/gain/XIRR), reusing
     the exact same tree the Portfolio page already renders from. */
  private portfolioTree: FamilyNode[] = [];

  loading = true;
  error = '';

  detailedRangeModalOpen = false;
  detailedRangeFrom = '';
  detailedRangeTo = '';
  detailedRangeFamily = '';
  detailedRangeError = '';

  summaryFamilyModalOpen = false;
  summaryFamily = '';

  expandedFamily = '';
  expandedSubClass = '';
  expandedUnderlying = '';

  downloadMenuOpen = false;

  /**
   * Distinct Family names for the download modals' Family filter,
   * alphabetically sorted. "All Families" is prepended in the
   * template, not here, since it isn't a real family value.
   */
  get familyOptions(): string[] {
    const names = new Set<string>();

    for (const family of this.families) {
      if (family.family_name) {
        names.add(family.family_name);
      }
    }

    return Array.from(names).sort((a, b) => a.localeCompare(b));
  }

  ngOnInit(): void {
    this.loadReports();
  }

  loadReports(): void {
    this.loading = true;
    this.error = '';

    this.portfolioApi.getTransactions().subscribe({
      next: (response) => {
        this.families = this.buildTree(response.results ?? []);

        this.portfolioApi.getPortfolioTree().subscribe({
          next: (treeResponse) => {
            this.portfolioTree = treeResponse.families ?? [];

            this.loading = false;
            this.cdr.detectChanges();
          },

          error: (error) => {
            console.error('Portfolio tree API error:', error);

            /* Transactions loaded fine, so the Reports tree itself
               still renders. Only the Summary download depends on
               portfolioTree, so we don't block the page on this. */
            this.portfolioTree = [];

            this.loading = false;
            this.cdr.detectChanges();
          },
        });
      },

      error: (error) => {
        console.error('Reports transactions API error:', error);

        this.loading = false;

        if (error?.status === 401 || error?.status === 403) {
          this.error = 'Authentication failed. Please log in again.';
        } else {
          this.error = 'Unable to load report data.';
        }

        this.cdr.detectChanges();
      },
    });
  }

  refresh(): void {
    this.loadReports();
  }

  /* ============================================================
     TREE BUILDING
     ============================================================ */

  private clean(value: string | null | undefined): string {
    const trimmed = value?.trim();
    return trimmed || UNASSIGNED;
  }

  private getUnderlyingName(tx: Transaction): string {
    return this.clean(tx.underlying || tx.asset_name);
  }

  private buildTree(transactions: Transaction[]): FamilyGroup[] {
    const familyMap = new Map<string, Map<string, Map<string, Transaction[]>>>();

    for (const tx of transactions) {
      const family = this.clean(tx.family_name);
      const subClass = this.clean(tx.sub_class);
      const underlying = this.getUnderlyingName(tx);

      if (!familyMap.has(family)) {
        familyMap.set(family, new Map());
      }

      const subClassMap = familyMap.get(family)!;

      if (!subClassMap.has(subClass)) {
        subClassMap.set(subClass, new Map());
      }

      const underlyingMap = subClassMap.get(subClass)!;

      if (!underlyingMap.has(underlying)) {
        underlyingMap.set(underlying, []);
      }

      underlyingMap.get(underlying)!.push(tx);
    }

    const families: FamilyGroup[] = Array.from(familyMap.entries())
      .map(([family_name, subClassMap]) => {
        const sub_classes: SubClassGroup[] = Array.from(subClassMap.entries())
          .map(([sub_class, underlyingMap]) => {
            const underlyings: UnderlyingGroup[] = Array.from(underlyingMap.entries())
              .map(([underlying, txs]) => ({ underlying, transactions: txs }))
              .sort((a, b) => a.underlying.localeCompare(b.underlying));

            const transaction_count = underlyings.reduce(
              (total, group) => total + group.transactions.length,
              0,
            );

            return { sub_class, underlyings, transaction_count };
          })
          .sort((a, b) => a.sub_class.localeCompare(b.sub_class));

        const transaction_count = sub_classes.reduce(
          (total, group) => total + group.transaction_count,
          0,
        );

        return { family_name, sub_classes, transaction_count };
      })
      .sort((a, b) => a.family_name.localeCompare(b.family_name));

    return families;
  }

  /* ============================================================
     EXPAND / COLLAPSE
     ============================================================ */

  toggleFamily(family: string): void {
    if (this.expandedFamily === family) {
      this.expandedFamily = '';
      this.expandedSubClass = '';
      this.expandedUnderlying = '';
      return;
    }

    this.expandedFamily = family;
    this.expandedSubClass = '';
    this.expandedUnderlying = '';
  }

  toggleSubClass(key: string): void {
    if (this.expandedSubClass === key) {
      this.expandedSubClass = '';
      this.expandedUnderlying = '';
      return;
    }

    this.expandedSubClass = key;
    this.expandedUnderlying = '';
  }

  toggleUnderlying(key: string): void {
    this.expandedUnderlying = this.expandedUnderlying === key ? '' : key;
  }

  getSubClassKey(family: string, subClass: string): string {
    return `${family}::${subClass}`;
  }

  getUnderlyingKey(family: string, subClass: string, underlying: string): string {
    return `${family}::${subClass}::${underlying}`;
  }

  trackByFamily(_index: number, group: FamilyGroup): string {
    return group.family_name;
  }

  trackBySubClass(_index: number, group: SubClassGroup): string {
    return group.sub_class;
  }

  trackByUnderlying(_index: number, group: UnderlyingGroup): string {
    return group.underlying;
  }

  trackByTransaction(_index: number, tx: Transaction): number {
    return tx.id;
  }

  /* ============================================================
     DOWNLOAD MENU
     ============================================================ */

  toggleDownloadMenu(): void {
    this.downloadMenuOpen = !this.downloadMenuOpen;
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    if (!this.downloadMenuOpen) {
      return;
    }

    if (!this.elementRef.nativeElement.contains(event.target)) {
      this.downloadMenuOpen = false;
    }
  }

  /**
   * Opens the Family prompt for the Summary View download.
   */
  openSummaryFamilyModal(): void {
    this.downloadMenuOpen = false;
    this.summaryFamily = '';
    this.summaryFamilyModalOpen = true;
  }

  cancelSummaryFamilyModal(): void {
    this.summaryFamilyModalOpen = false;
  }

  async confirmSummaryDownload(): Promise<void> {
    this.summaryFamilyModalOpen = false;

    const rows = this.buildSummaryRows(this.summaryFamily);

    const familyLabel = this.summaryFamily || 'All Families';

    const familySlug = this.summaryFamily ? `_${this.slugify(this.summaryFamily)}` : '';

    await this.exportWorkbook({
      sheetName: 'Summary',
      title: `Portfolio Summary — ${familyLabel} (as of ${this.todayLabel()})`,
      columns: [
        { header: 'Family', key: 'family_name', width: 24 },
        { header: 'Sub Class', key: 'sub_class', width: 22 },
        { header: 'Quantity', key: 'quantity', width: 16, numFmt: '#,##,##0.00' },
        { header: 'Invested Amount', key: 'invested_value', width: 20, numFmt: '"₹"#,##,##0' },
        { header: 'Current Value', key: 'current_value', width: 20, numFmt: '"₹"#,##,##0' },
        { header: 'Gain/Loss', key: 'gain', width: 20, numFmt: '"₹"#,##,##0' },
        { header: 'XIRR (%)', key: 'xirr', width: 14, numFmt: '0.00"%"' },
      ],
      rows: rows.map((row) => ({
        family_name: row.family_name,
        sub_class: row.sub_class,
        quantity: row.quantity,
        invested_value: row.invested_value,
        current_value: row.current_value,
        gain: row.gain,
        xirr: row.xirr,
      })),
      gainKey: 'gain',
      filename: `portfolio_summary${familySlug}_${this.todayStamp()}.xlsx`,
    });
  }

  /**
   * Opens the date-range prompt for the Detailed View download.
   * Prefills From/To with the earliest/latest transaction dates
   * actually present, so the default range covers everything and
   * the user only needs to narrow it if they want a subset.
   */
  openDetailedRangeModal(): void {
    this.downloadMenuOpen = false;
    this.detailedRangeError = '';
    this.detailedRangeFamily = '';

    const dates = this.allTransactionDates();

    this.detailedRangeFrom = dates.length ? dates[0] : '';
    this.detailedRangeTo = dates.length ? dates[dates.length - 1] : '';

    this.detailedRangeModalOpen = true;
  }

  cancelDetailedRangeModal(): void {
    this.detailedRangeModalOpen = false;
    this.detailedRangeError = '';
  }

  async confirmDetailedRangeDownload(): Promise<void> {
    if (
      this.detailedRangeFrom &&
      this.detailedRangeTo &&
      this.detailedRangeFrom > this.detailedRangeTo
    ) {
      this.detailedRangeError = 'From date must be on or before To date.';
      return;
    }

    this.detailedRangeError = '';
    this.detailedRangeModalOpen = false;

    const rows = this.buildDetailedRows(
      this.detailedRangeFrom,
      this.detailedRangeTo,
      this.detailedRangeFamily,
    );

    const rangeLabel = this.formatRangeLabel(this.detailedRangeFrom, this.detailedRangeTo);

    const familyLabel = this.detailedRangeFamily || 'All Families';

    const familySlug = this.detailedRangeFamily ? `_${this.slugify(this.detailedRangeFamily)}` : '';

    await this.exportWorkbook({
      sheetName: 'Detailed',
      title: `Portfolio Detailed — ${familyLabel} (${rangeLabel})`,
      columns: [
        { header: 'Family', key: 'family_name', width: 24 },
        { header: 'Sub Class', key: 'sub_class', width: 20 },
        { header: 'Underlying', key: 'underlying', width: 28 },
        { header: 'ISIN', key: 'isin', width: 16 },
        { header: 'Transaction Date', key: 'transaction_date', width: 18, numFmt: 'dd-mmm-yyyy' },
        { header: 'Transaction Type', key: 'transaction_type', width: 18 },
        { header: 'Quantity', key: 'quantity', width: 14, numFmt: '#,##,##0.00' },
        { header: 'Price', key: 'price_per_unit', width: 16, numFmt: '"₹"#,##,##0.00' },
        { header: 'Amount', key: 'amount', width: 18, numFmt: '"₹"#,##,##0' },
      ],
      rows,
      filename: `portfolio_detailed${familySlug}_${this.detailedRangeFrom || 'start'}_to_${this.detailedRangeTo || 'end'}.xlsx`,
    });
  }

  /**
   * Lowercases and replaces anything that isn't alphanumeric with
   * an underscore, for building a safe filename segment from a
   * Family name.
   */
  private slugify(value: string): string {
    return value
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/^_+|_+$/g, '');
  }

  /**
   * Every transaction's ISO date string ("YYYY-MM-DD"), sorted
   * ascending. Used only to prefill the date-range modal's default
   * From/To with the actual earliest/latest dates in the data.
   */
  private allTransactionDates(): string[] {
    const dates: string[] = [];

    for (const family of this.families) {
      for (const subClass of family.sub_classes) {
        for (const underlyingGroup of subClass.underlyings) {
          for (const tx of underlyingGroup.transactions) {
            if (tx.transaction_date) {
              dates.push(tx.transaction_date);
            }
          }
        }
      }
    }

    return dates.sort();
  }

  /**
   * Flattens the Family -> Sub Class -> Underlying -> Transactions
   * tree into rows for the Detailed download, filtered to the
   * given date range (inclusive; an empty bound means unbounded on
   * that side) and optionally to one Family (an empty value means
   * all Families), and sorted by Transaction Date across the whole
   * sheet (most recent first) - so the export is indexed by date
   * rather than clustered by Underlying. Family/Sub Class/Underlying
   * are still included as columns on every row so the hierarchy
   * stays identifiable per the Detailed View's requirements.
   */
  private buildDetailedRows(from: string, to: string, family?: string): Record<string, unknown>[] {
    const flat: {
      family_name: string;
      sub_class: string;
      underlying: string;
      tx: Transaction;
    }[] = [];

    for (const familyGroup of this.families) {
      if (family && familyGroup.family_name !== family) {
        continue;
      }

      for (const subClass of familyGroup.sub_classes) {
        for (const underlyingGroup of subClass.underlyings) {
          for (const tx of underlyingGroup.transactions) {
            if (!tx.transaction_date) {
              continue;
            }

            if (from && tx.transaction_date < from) {
              continue;
            }

            if (to && tx.transaction_date > to) {
              continue;
            }

            flat.push({
              family_name: familyGroup.family_name,
              sub_class: subClass.sub_class,
              underlying: underlyingGroup.underlying,
              tx,
            });
          }
        }
      }
    }

    flat.sort((a, b) => b.tx.transaction_date.localeCompare(a.tx.transaction_date));

    return flat.map(({ family_name, sub_class, underlying, tx }) => ({
      family_name,
      sub_class,
      underlying,
      isin: tx.isin || '-',
      transaction_date: new Date(tx.transaction_date),
      transaction_type: tx.transaction_type_display || tx.transaction_type,
      quantity: this.toNumber(tx.quantity),
      price_per_unit: this.toNumber(tx.price_per_unit),
      amount: this.toNumber(tx.amount),
    }));
  }

  private formatRangeLabel(from: string, to: string): string {
    if (!from && !to) {
      return 'All dates';
    }

    const formatOne = (value: string) =>
      new Intl.DateTimeFormat('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }).format(
        new Date(value),
      );

    if (from && to) {
      return `${formatOne(from)} – ${formatOne(to)}`;
    }

    return from ? `From ${formatOne(from)}` : `Up to ${formatOne(to)}`;
  }

  /**
   * Family -> Sub Class aggregation for the Summary View download.
   *
   * Reuses the same portfolio tree (and the same per-asset
   * quantity/invested_value/current_value/pnl/xirr fields) the
   * Portfolio page's own subClassSummaries getter aggregates from -
   * this only adds Family as an additional grouping key, since the
   * Summary View must be Family -> Sub Class, not just Sub Class.
   *
   * An optional family filters the result to that one Family; an
   * empty value returns all Families.
   */
  private buildSummaryRows(family?: string): SubClassSummaryRow[] {
    const rowMap = new Map<
      string,
      SubClassSummaryRow & { assets: { invested_value: number; xirr: number | null }[] }
    >();

    for (const familyNode of this.portfolioTree) {
      if (family && familyNode.family_name !== family) {
        continue;
      }

      for (const portfolio of familyNode.portfolios) {
        for (const assetClass of portfolio.asset_classes) {
          for (const subClass of assetClass.sub_classes) {
            const key = `${familyNode.family_name}::${subClass.sub_class}`;

            let row = rowMap.get(key);

            if (!row) {
              row = {
                family_name: familyNode.family_name,
                sub_class: subClass.sub_class,
                quantity: 0,
                invested_value: 0,
                current_value: 0,
                gain: 0,
                xirr: null,
                assets: [],
              };

              rowMap.set(key, row);
            }

            for (const asset of subClass.assets) {
              row.quantity += this.toNumber(asset.quantity);
              row.invested_value += this.toNumber(asset.invested_value);
              row.current_value += this.toNumber(asset.current_value);
              row.gain += this.toNumber(asset.pnl);

              row.assets.push({
                invested_value: this.toNumber(asset.invested_value),
                xirr: asset.xirr,
              });
            }
          }
        }
      }
    }

    return Array.from(rowMap.values())
      .map((row) => ({
        family_name: row.family_name,
        sub_class: row.sub_class,
        quantity: row.quantity,
        invested_value: row.invested_value,
        current_value: row.current_value,
        gain: row.gain,
        xirr: this.weightedXirr(row.assets),
      }))
      .sort(
        (a, b) =>
          a.family_name.localeCompare(b.family_name) || a.sub_class.localeCompare(b.sub_class),
      );
  }

  private weightedXirr(assets: { invested_value: number; xirr: number | null }[]): number | null {
    const validAssets = assets.filter(
      (asset) => asset.xirr !== null && asset.xirr !== undefined && asset.invested_value > 0,
    );

    if (!validAssets.length) {
      return null;
    }

    let weightedXirr = 0;
    let totalInvested = 0;

    for (const asset of validAssets) {
      weightedXirr += (asset.xirr as number) * asset.invested_value;
      totalInvested += asset.invested_value;
    }

    return totalInvested ? weightedXirr / totalInvested : null;
  }

  /* ============================================================
     EXCEL EXPORT
     ============================================================ */

  /**
   * Builds a single-sheet, styled .xlsx workbook and downloads it.
   *
   * Styling is purely cosmetic (title band, header fill/borders,
   * frozen header row, autofilter, column number formats, banded
   * rows, green/red Gain-Loss coloring) - the underlying values are
   * exactly the rows passed in, which the callers build from the
   * same tree/aggregation used to render the page.
   */
  private async exportWorkbook(config: {
    sheetName: string;
    title: string;
    columns: { header: string; key: string; width: number; numFmt?: string }[];
    rows: Record<string, unknown>[];
    gainKey?: string;
    filename: string;
  }): Promise<void> {
    const { default: ExcelJSLib } = await import('exceljs');

    const workbook = new ExcelJSLib.Workbook();
    workbook.creator = 'PWMS';
    workbook.created = new Date();

    const sheet = workbook.addWorksheet(config.sheetName, {
      views: [{ state: 'frozen', ySplit: 2 }],
    });

    const columnCount = config.columns.length;

    /* Title band */
    sheet.mergeCells(1, 1, 1, columnCount);
    const titleCell = sheet.getCell(1, 1);
    titleCell.value = config.title;
    titleCell.font = { bold: true, size: 12, color: { argb: 'FFFFFFFF' } };
    titleCell.fill = {
      type: 'pattern',
      pattern: 'solid',
      fgColor: { argb: 'FF111827' },
    };
    titleCell.alignment = { vertical: 'middle', horizontal: 'left' };
    sheet.getRow(1).height = 26;

    /* Header row */
    const headerRow = sheet.getRow(2);
    config.columns.forEach((col, index) => {
      const cell = headerRow.getCell(index + 1);
      cell.value = col.header;
      cell.font = { bold: true, color: { argb: 'FF101828' } };
      cell.fill = {
        type: 'pattern',
        pattern: 'solid',
        fgColor: { argb: 'FFF8FAFC' },
      };
      cell.border = {
        top: { style: 'thin', color: { argb: 'FFE5E7EB' } },
        bottom: { style: 'thin', color: { argb: 'FFE5E7EB' } },
        left: { style: 'thin', color: { argb: 'FFE5E7EB' } },
        right: { style: 'thin', color: { argb: 'FFE5E7EB' } },
      };
      cell.alignment = { vertical: 'middle' };
    });
    headerRow.height = 20;

    sheet.columns = config.columns.map((col) => ({
      key: col.key,
      width: col.width,
      style: col.numFmt ? { numFmt: col.numFmt } : undefined,
    }));

    /* Data rows */
    config.rows.forEach((rowData, rowIndex) => {
      const row = sheet.addRow(rowData);
      const isBanded = rowIndex % 2 === 1;

      row.eachCell((cell) => {
        cell.border = {
          top: { style: 'thin', color: { argb: 'FFEEF0F3' } },
          bottom: { style: 'thin', color: { argb: 'FFEEF0F3' } },
          left: { style: 'thin', color: { argb: 'FFEEF0F3' } },
          right: { style: 'thin', color: { argb: 'FFEEF0F3' } },
        };

        if (isBanded) {
          cell.fill = {
            type: 'pattern',
            pattern: 'solid',
            fgColor: { argb: 'FFF8FAFC' },
          };
        }
      });

      if (config.gainKey) {
        const gainValue = Number(rowData[config.gainKey]);
        const gainCell = row.getCell(config.gainKey);

        gainCell.font = {
          color: { argb: gainValue >= 0 ? 'FF16A34A' : 'FFDC2626' },
          bold: true,
        };
      }
    });

    sheet.autoFilter = {
      from: { row: 2, column: 1 },
      to: { row: 2, column: columnCount },
    };

    const buffer = await workbook.xlsx.writeBuffer();

    const blob = new Blob([buffer], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });

    this.triggerDownload(blob, config.filename);
  }

  private triggerDownload(blob: Blob, filename: string): void {
    const url = URL.createObjectURL(blob);

    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    anchor.style.display = 'none';

    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);

    URL.revokeObjectURL(url);
  }

  private todayStamp(): string {
    const now = new Date();

    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');

    return `${year}-${month}-${day}`;
  }

  private todayLabel(): string {
    return new Intl.DateTimeFormat('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    }).format(new Date());
  }

  /* ============================================================
     DISPLAY FORMATTING
     (same helpers/format conventions as portfolio.component.ts)
     ============================================================ */

  formatCurrency(value: number): string {
    return new Intl.NumberFormat('en-IN', {
      maximumFractionDigits: 0,
    }).format(this.toNumber(value));
  }

  formatNumber(value: number): string {
    return new Intl.NumberFormat('en-IN', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    }).format(this.toNumber(value));
  }

  formatDecimal(value: number): string {
    return new Intl.NumberFormat('en-IN', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(this.toNumber(value));
  }

  private toNumber(value: number | null | undefined): number {
    if (value === null || value === undefined) {
      return 0;
    }

    const numberValue = Number(value);

    return Number.isFinite(numberValue) ? numberValue : 0;
  }
}
