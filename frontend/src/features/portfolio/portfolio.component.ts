import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ChangeDetectorRef, Component, OnDestroy, OnInit, inject } from '@angular/core';
import { Subscription, timer } from 'rxjs';

import {
  PortfolioApiService,
  PortfolioAssetNode,
  FamilyNode,
  SubClassNode,
} from '../../core/services/portfolio-api.service';

import { ManualPriceService } from '../../core/services/manual-price.service';

interface SubClassSummary {
  sub_class: string;
  current_value: number;
  pnl: number;
  quantity: number;
  xirr: number | null;
  assets: PortfolioAssetNode[];
}

@Component({
  selector: 'app-portfolio',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './portfolio.component.html',
  styleUrl: './portfolio.component.scss',
})
export class PortfolioComponent implements OnInit, OnDestroy {
  private readonly portfolioApi = inject(PortfolioApiService);
  private readonly manualPriceService = inject(ManualPriceService);
  private readonly cdr = inject(ChangeDetectorRef);

  private refreshSubscription: Subscription | null = null;

  families: FamilyNode[] = [];

  selectedFamily = '';
  selectedAssetClass = '';

  expandedSubClass = '';

  loading = true;
  error = '';

  /**
   * Asset currently being edited.
   */
  editingAssetId: number | null = null;

  /**
   * Temporary manual price entered by the user.
   */
  manualPriceInput = '';

  /**
   * Asset currently being saved.
   */
  savingManualPriceAssetId: number | null = null;

  /**
   * Per-asset error messages.
   */
  manualPriceErrors: Record<number, string> = {};

  ngOnInit(): void {
    this.loadPortfolio();

    this.refreshSubscription = timer(30000, 30000).subscribe(() => {
      this.loadPortfolio(true);
    });
  }

  ngOnDestroy(): void {
    this.refreshSubscription?.unsubscribe();
  }

  loadPortfolio(silent = false): void {
    if (!silent) {
      this.loading = true;
      this.error = '';
    }

    this.portfolioApi.getPortfolioTree().subscribe({
      next: (response) => {
        this.families = response.families ?? [];

        this.validateSelections();

        this.loading = false;

        this.cdr.detectChanges();
      },

      error: (error) => {
        console.error('Portfolio API error:', error);

        this.loading = false;

        if (error?.status === 401 || error?.status === 403) {
          this.error = 'Authentication failed. Please log in again.';
        } else {
          this.error = 'Unable to load portfolio data.';
        }

        this.cdr.detectChanges();
      },
    });
  }

  refresh(): void {
    this.loadPortfolio();
  }

  get familyOptions(): string[] {
    return this.families
      .map((family) => family.family_name)
      .filter(Boolean)
      .sort((a, b) => a.localeCompare(b));
  }

  get assetClassOptions(): string[] {
    const classes = new Set<string>();

    for (const family of this.filteredFamilies) {
      for (const portfolio of family.portfolios) {
        for (const assetClass of portfolio.asset_classes) {
          if (assetClass.asset_class) {
            classes.add(assetClass.asset_class);
          }
        }
      }
    }

    return Array.from(classes).sort((a, b) => a.localeCompare(b));
  }

  get filteredFamilies(): FamilyNode[] {
    if (!this.selectedFamily) {
      return this.families;
    }

    return this.families.filter((family) => family.family_name === this.selectedFamily);
  }

  get subClassSummaries(): SubClassSummary[] {
    const summaryMap = new Map<string, SubClassSummary>();

    for (const family of this.filteredFamilies) {
      for (const portfolio of family.portfolios) {
        for (const assetClass of portfolio.asset_classes) {
          if (this.selectedAssetClass && assetClass.asset_class !== this.selectedAssetClass) {
            continue;
          }

          for (const subClass of assetClass.sub_classes) {
            const key = subClass.sub_class || 'Unassigned';

            let summary = summaryMap.get(key);

            if (!summary) {
              summary = {
                sub_class: key,
                current_value: 0,
                pnl: 0,
                quantity: 0,
                xirr: null,
                assets: [],
              };

              summaryMap.set(key, summary);
            }

            summary.current_value += this.getSubClassCurrentValue(subClass);
            summary.pnl += this.getSubClassPnl(subClass);
            summary.quantity += this.getSubClassQuantity(subClass);
            summary.assets.push(...subClass.assets);
          }
        }
      }
    }

    return Array.from(summaryMap.values())
      .map((summary) => ({
        ...summary,
        xirr: this.calculateXirr(summary.assets),
      }))
      .sort((a, b) => a.sub_class.localeCompare(b.sub_class));
  }

  getSubClassAssets(subClass: string): PortfolioAssetNode[] {
    return this.subClassSummaries.find((summary) => summary.sub_class === subClass)?.assets ?? [];
  }

  toggleSubClass(subClass: string): void {
    this.expandedSubClass = this.expandedSubClass === subClass ? '' : subClass;
  }

  selectFamily(family: string): void {
    this.selectedFamily = this.selectedFamily === family ? '' : family;

    this.selectedAssetClass = '';
    this.expandedSubClass = '';
  }

  selectAssetClass(assetClass: string): void {
    this.selectedAssetClass = this.selectedAssetClass === assetClass ? '' : assetClass;

    this.expandedSubClass = '';
  }

  clearFamily(): void {
    this.selectedFamily = '';
    this.selectedAssetClass = '';
    this.expandedSubClass = '';
  }

  clearAssetClass(): void {
    this.selectedAssetClass = '';
    this.expandedSubClass = '';
  }

  isFamilySelected(family: string): boolean {
    return this.selectedFamily === family;
  }

  isAssetClassSelected(assetClass: string): boolean {
    return this.selectedAssetClass === assetClass;
  }

  /**
   * Start editing an asset's current price.
   */
  startEditingPrice(asset: PortfolioAssetNode): void {
    this.editingAssetId = asset.id;

    this.manualPriceInput =
      asset.current_price !== null && asset.current_price !== undefined
        ? String(asset.current_price)
        : '';

    this.manualPriceErrors[asset.id] = '';
  }

  /**
   * Cancel manual price editing.
   */
  cancelEditingPrice(asset: PortfolioAssetNode): void {
    this.editingAssetId = null;
    this.manualPriceInput = '';

    this.manualPriceErrors[asset.id] = '';
  }

  /**
   * Save a manually entered current price.
   */
  saveManualPrice(asset: PortfolioAssetNode): void {
    const price = Number(this.manualPriceInput);

    if (!Number.isFinite(price) || price <= 0) {
      this.manualPriceErrors[asset.id] = 'Enter a valid price greater than 0.';
      return;
    }

    this.manualPriceErrors[asset.id] = '';

    this.savingManualPriceAssetId = asset.id;

    this.manualPriceService.updatePrice(asset.id, price).subscribe({
      next: (response) => {
        this.savingManualPriceAssetId = null;

        if (!response.success) {
          this.manualPriceErrors[asset.id] = response.message || 'Unable to update price.';
          this.cdr.detectChanges();
          return;
        }

        this.editingAssetId = null;
        this.manualPriceInput = '';

        /*
         * Reload the portfolio tree so that:
         *
         * Current Value
         * P&L
         * P&L %
         * XIRR
         *
         * are all recalculated from the new price by the backend.
         */
        this.loadPortfolio(true);
      },

      error: (error) => {
        console.error('Manual price update failed:', error);

        this.savingManualPriceAssetId = null;

        this.manualPriceErrors[asset.id] =
          error?.error?.message || 'Unable to update manual price.';

        this.cdr.detectChanges();
      },
    });
  }

  /**
   * Check whether an asset is currently being edited.
   */
  isEditingPrice(asset: PortfolioAssetNode): boolean {
    return this.editingAssetId === asset.id;
  }

  /**
   * Check whether an asset price is currently being saved.
   */
  isSavingManualPrice(asset: PortfolioAssetNode): boolean {
    return this.savingManualPriceAssetId === asset.id;
  }

  /**
   * Get the manual-price error for an asset.
   */
  getManualPriceError(asset: PortfolioAssetNode): string {
    return this.manualPriceErrors[asset.id] || '';
  }

  /**
   * Returns the absolute value without exposing Math
   * directly to the Angular template.
   */
  formatAbsoluteCurrency(value: number): string {
    return this.formatCurrency(Math.abs(this.toNumber(value)));
  }

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

  formatPercentage(value: number | null): string {
    if (value === null || value === undefined) {
      return '-';
    }

    return `${this.formatDecimal(value)}%`;
  }

  getPnlClass(value: number): string {
    if (value > 0) {
      return 'positive';
    }

    if (value < 0) {
      return 'negative';
    }

    return 'neutral';
  }

  /**
   * Price date support.
   *
   * These methods safely support the current PortfolioAssetNode
   * even if the backend has not yet exposed a price date.
   */
  hasPriceDate(asset: PortfolioAssetNode): boolean {
    return !!this.getPriceDate(asset);
  }

  getPriceDate(asset: PortfolioAssetNode): string | null {
    const extendedAsset = asset as PortfolioAssetNode & {
      price_date?: string | null;
      updated_at?: string | null;
    };

    return extendedAsset.price_date ?? extendedAsset.updated_at ?? null;
  }

  formatPriceDate(dateValue: string | null): string {
    if (!dateValue) {
      return '';
    }

    const parsedDate = new Date(dateValue);

    if (Number.isNaN(parsedDate.getTime())) {
      return '';
    }

    return new Intl.DateTimeFormat('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    }).format(parsedDate);
  }

  private getSubClassCurrentValue(subClass: SubClassNode): number {
    return subClass.assets.reduce((total, asset) => total + this.toNumber(asset.current_value), 0);
  }

  private getSubClassPnl(subClass: SubClassNode): number {
    return subClass.assets.reduce((total, asset) => total + this.toNumber(asset.pnl), 0);
  }

  private getSubClassQuantity(subClass: SubClassNode): number {
    return subClass.assets.reduce((total, asset) => total + this.toNumber(asset.quantity), 0);
  }

  private calculateXirr(assets: PortfolioAssetNode[]): number | null {
    const validAssets = assets.filter(
      (asset) =>
        asset.xirr !== null && asset.xirr !== undefined && this.toNumber(asset.invested_value) > 0,
    );

    if (!validAssets.length) {
      return null;
    }

    let weightedXirr = 0;
    let totalInvested = 0;

    for (const asset of validAssets) {
      const invested = this.toNumber(asset.invested_value);

      const xirr = this.toNumber(asset.xirr);

      weightedXirr += xirr * invested;
      totalInvested += invested;
    }

    return totalInvested ? weightedXirr / totalInvested : null;
  }

  private toNumber(value: number | null | undefined): number {
    if (value === null || value === undefined) {
      return 0;
    }

    const numberValue = Number(value);

    return Number.isFinite(numberValue) ? numberValue : 0;
  }

  private validateSelections(): void {
    if (this.selectedFamily && !this.familyOptions.includes(this.selectedFamily)) {
      this.selectedFamily = '';
    }

    if (this.selectedAssetClass && !this.assetClassOptions.includes(this.selectedAssetClass)) {
      this.selectedAssetClass = '';
    }

    if (
      this.expandedSubClass &&
      !this.subClassSummaries.some((summary) => summary.sub_class === this.expandedSubClass)
    ) {
      this.expandedSubClass = '';
    }
  }
}
