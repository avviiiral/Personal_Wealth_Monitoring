import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnDestroy, OnInit, inject } from '@angular/core';
import { Subscription, timer } from 'rxjs';

import {
  AssetClassNode,
  FamilyNode,
  PortfolioApiService,
  PortfolioAssetNode,
  SubClassNode,
} from '../../core/services/portfolio-api.service';

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
  imports: [CommonModule],
  templateUrl: './portfolio.component.html',
  styleUrl: './portfolio.component.scss',
})
export class PortfolioComponent implements OnInit, OnDestroy {
  private readonly portfolioApi = inject(PortfolioApiService);
  private readonly cdr = inject(ChangeDetectorRef);

  private refreshSubscription: Subscription | null = null;

  families: FamilyNode[] = [];

  selectedFamily = '';
  selectedAssetClass = '';

  expandedSubClass = '';

  loading = true;
  error = '';

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
