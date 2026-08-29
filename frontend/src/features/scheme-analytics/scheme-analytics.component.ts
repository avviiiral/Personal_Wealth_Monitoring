import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';

import {
  PortfolioApiService,
  PortfolioAssetNode,
  PortfolioTreeResponse,
} from '../../core/services/portfolio-api.service';

/**
 * Flattened row: every underlying asset across every
 * Family/Portfolio/AssetClass/SubClass, with the hierarchy fields
 * carried along for the Category/Family/Advisor columns.
 *
 * Columns NOT included, and why:
 *   - Benchmark / Benchmark Return: no benchmark data source exists
 *     yet (see the standing gap noted throughout this project).
 *   - Fund Manager, Inception Date: no field on Asset/Holding/
 *     Transaction — not fabricated here.
 * Everything else in this row is a real field already returned by
 * PortfolioTreeService.build() (family/advisor/amc/quant fields
 * added in investments/migrations/0007_... last session).
 */
interface SchemeRow extends PortfolioAssetNode {
  asset_class: string;
  sub_class: string;
}

type SortKey =
  | 'asset_name'
  | 'asset_class'
  | 'sub_class'
  | 'family_name'
  | 'advisors'
  | 'amc_name'
  | 'invested_value'
  | 'current_value'
  | 'pnl'
  | 'pnl_percentage'
  | 'xirr';

/**
 * SCHEME ANALYTICS
 *
 * A single flat, sortable/searchable/paginated table across every
 * scheme/instrument in the portfolio, built entirely client-side
 * from the existing Portfolio Tree API — no new backend endpoint
 * needed, since PortfolioTreeService.build() already returns every
 * field this table needs (including the SecurityMaster-sourced
 * amc_name/credit_rating/etc. added in the previous session).
 */
@Component({
  selector: 'app-scheme-analytics',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './scheme-analytics.component.html',
  styleUrl: './scheme-analytics.component.scss',
})
export class SchemeAnalyticsComponent implements OnInit {
  private readonly portfolioApi = inject(PortfolioApiService);
  private readonly cdr = inject(ChangeDetectorRef);

  loading = true;
  error = '';

  private allRows: SchemeRow[] = [];

  searchTerm = '';
  sortKey: SortKey = 'current_value';
  sortDescending = true;

  page = 1;
  readonly pageSize = 25;

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading = true;
    this.error = '';

    this.portfolioApi.getPortfolioTree().subscribe({
      next: (data: PortfolioTreeResponse) => {
        this.allRows = this.flatten(data);
        this.loading = false;
        this.page = 1;
        this.cdr.markForCheck();
      },

      error: (error) => {
        console.error('SCHEME ANALYTICS TREE ERROR:', error);

        this.loading = false;
        this.error = 'Unable to load scheme data.';
        this.cdr.markForCheck();
      },
    });
  }

  private flatten(tree: PortfolioTreeResponse): SchemeRow[] {
    const rows: SchemeRow[] = [];

    for (const family of tree.families ?? []) {
      for (const portfolio of family.portfolios ?? []) {
        for (const assetClass of portfolio.asset_classes ?? []) {
          for (const subClass of assetClass.sub_classes ?? []) {
            for (const asset of subClass.assets ?? []) {
              rows.push({
                ...asset,
                asset_class: assetClass.asset_class,
                sub_class: subClass.sub_class,
              });
            }
          }
        }
      }
    }

    return rows;
  }

  setSort(key: SortKey): void {
    if (this.sortKey === key) {
      this.sortDescending = !this.sortDescending;
    } else {
      this.sortKey = key;
      this.sortDescending = true;
    }

    this.page = 1;
  }

  sortIndicator(key: SortKey): string {
    if (this.sortKey !== key) {
      return '';
    }

    return this.sortDescending ? '▼' : '▲';
  }

  onSearchChange(): void {
    this.page = 1;
  }

  private matchesSearch(row: SchemeRow): boolean {
    const term = this.searchTerm.trim().toLowerCase();

    if (!term) {
      return true;
    }

    const haystack = [
      row.asset_name,
      row.underlying,
      row.family_name,
      row.advisors,
      row.amc_name ?? '',
      row.asset_class,
      row.sub_class,
      row.isin ?? '',
    ]
      .join(' ')
      .toLowerCase();

    return haystack.includes(term);
  }

  get filteredRows(): SchemeRow[] {
    const filtered = this.allRows.filter((row) => this.matchesSearch(row));

    const key = this.sortKey;
    const direction = this.sortDescending ? -1 : 1;

    return [...filtered].sort((a, b) => {
      const aValue = a[key];
      const bValue = b[key];

      if (aValue === null || aValue === undefined) return 1;
      if (bValue === null || bValue === undefined) return -1;

      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return (aValue - bValue) * direction;
      }

      return String(aValue).localeCompare(String(bValue)) * direction;
    });
  }

  get pagedRows(): SchemeRow[] {
    const start = (this.page - 1) * this.pageSize;
    return this.filteredRows.slice(start, start + this.pageSize);
  }

  get totalPages(): number {
    return Math.max(1, Math.ceil(this.filteredRows.length / this.pageSize));
  }

  get pageStart(): number {
    return this.filteredRows.length === 0 ? 0 : (this.page - 1) * this.pageSize + 1;
  }

  get pageEnd(): number {
    return Math.min(this.page * this.pageSize, this.filteredRows.length);
  }

  goToPage(page: number): void {
    if (page < 1 || page > this.totalPages) {
      return;
    }

    this.page = page;
  }

  trackByAssetId(_index: number, row: SchemeRow): number {
    return row.id;
  }

  formatCurrency(value: number | null | undefined): string {
    if (value === null || value === undefined) {
      return '-';
    }

    return `₹${value.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
  }

  formatPercentage(value: number | null | undefined): string {
    if (value === null || value === undefined) {
      return '-';
    }

    return `${value.toFixed(2)}%`;
  }

  getPnlClass(value: number | null | undefined): string {
    if (value === null || value === undefined || value === 0) {
      return 'neutral';
    }

    return value > 0 ? 'positive' : 'negative';
  }
}
