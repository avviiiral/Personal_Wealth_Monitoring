import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ChangeDetectorRef, Component, OnDestroy, OnInit, inject } from '@angular/core';
import { Subscription, timer } from 'rxjs';

import {
  AssetClassNode,
  FamilyNode,
  PortfolioApiService,
} from '../../core/services/portfolio-api.service';

@Component({
  selector: 'app-portfolio',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './portfolio.component.html',
  styleUrl: './portfolio.component.scss',
})
export class PortfolioComponent implements OnInit, OnDestroy {
  private readonly portfolioApi = inject(PortfolioApiService);

  private readonly cdr = inject(ChangeDetectorRef);

  private refreshSubscription: Subscription | null = null;

  // ==========================================================
  // DATA
  // ==========================================================

  families: FamilyNode[] = [];

  // ==========================================================
  // FILTERS
  // ==========================================================

  selectedFamily = '';

  selectedAssetClass = '';

  // ==========================================================
  // PORTFOLIO EXPANSION
  // ==========================================================

  expandedPortfolio: string | null = null;

  // ==========================================================
  // STATE
  // ==========================================================

  loading = true;

  error = '';

  // ==========================================================
  // INIT
  // ==========================================================

  ngOnInit(): void {
    this.loadPortfolio();

    /*
     * Check the backend periodically so that if the Excel
     * file is updated, the Family / Asset Class buttons and
     * Portfolio data update automatically.
     *
     * Current interval: 30 seconds.
     */

    this.refreshSubscription = timer(30000, 30000).subscribe(() => {
      this.loadPortfolio(true);
    });
  }

  // ==========================================================
  // DESTROY
  // ==========================================================

  ngOnDestroy(): void {
    this.refreshSubscription?.unsubscribe();
  }

  // ==========================================================
  // LOAD PORTFOLIO
  // ==========================================================

  loadPortfolio(silent = false): void {
    if (!silent) {
      this.loading = true;

      this.error = '';
    }

    this.portfolioApi.getPortfolioTree().subscribe({
      next: (response) => {
        const previousFamily = this.selectedFamily;

        const previousAssetClass = this.selectedAssetClass;

        this.families = response.results ?? [];

        // --------------------------------------------------
        // Preserve selected Family if it still exists
        // --------------------------------------------------

        const familyStillExists = this.families.some(
          (family) => family.family_name === previousFamily,
        );

        if (previousFamily && !familyStillExists) {
          this.selectedFamily = '';

          this.selectedAssetClass = '';

          this.expandedPortfolio = null;
        }

        // --------------------------------------------------
        // Preserve selected Asset Class if it still exists
        // --------------------------------------------------

        if (
          previousAssetClass &&
          !this.availableAssetClasses.some(
            (assetClass) => assetClass.asset_class === previousAssetClass,
          )
        ) {
          this.selectedAssetClass = '';

          this.expandedPortfolio = null;
        }

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

  // ==========================================================
  // MANUAL REFRESH
  // ==========================================================

  refresh(): void {
    this.loadPortfolio();
  }

  // ==========================================================
  // FAMILY BUTTONS
  // ==========================================================

  get familyOptions(): string[] {
    return this.families
      .map((family) => family.family_name)
      .filter((name) => !!name)
      .sort((a, b) => a.localeCompare(b));
  }

  // ==========================================================
  // ASSET CLASS BUTTONS
  // ==========================================================

  get availableAssetClasses(): AssetClassNode[] {
    const assetClassMap = new Map<string, AssetClassNode>();

    for (const family of this.families) {
      for (const assetClass of family.asset_classes) {
        if (!assetClassMap.has(assetClass.asset_class)) {
          assetClassMap.set(assetClass.asset_class, assetClass);
        }
      }
    }

    return Array.from(assetClassMap.values()).sort((a, b) =>
      a.asset_class.localeCompare(b.asset_class),
    );
  }

  // ==========================================================
  // SELECT FAMILY
  // ==========================================================

  selectFamily(familyName: string): void {
    if (this.selectedFamily === familyName) {
      /*
       * Clicking the selected family again
       * clears the Family filter.
       */

      this.selectedFamily = '';
    } else {
      this.selectedFamily = familyName;
    }

    this.expandedPortfolio = null;
  }

  // ==========================================================
  // SELECT ASSET CLASS
  // ==========================================================

  selectAssetClass(assetClass: string): void {
    if (this.selectedAssetClass === assetClass) {
      /*
       * Clicking the selected asset class
       * again clears the filter.
       */

      this.selectedAssetClass = '';
    } else {
      this.selectedAssetClass = assetClass;
    }

    this.expandedPortfolio = null;
  }

  // ==========================================================
  // CLEAR FAMILY
  // ==========================================================

  clearFamily(): void {
    this.selectedFamily = '';

    this.expandedPortfolio = null;
  }

  // ==========================================================
  // CLEAR ASSET CLASS
  // ==========================================================

  clearAssetClass(): void {
    this.selectedAssetClass = '';

    this.expandedPortfolio = null;
  }

  // ==========================================================
  // SELECTED FAMILY DATA
  // ==========================================================

  get selectedFamilyData(): FamilyNode | null {
    if (!this.selectedFamily) {
      return null;
    }

    return this.families.find((family) => family.family_name === this.selectedFamily) ?? null;
  }

  // ==========================================================
  // FILTERED FAMILIES
  // ==========================================================

  get filteredFamilies(): FamilyNode[] {
    if (!this.selectedFamily) {
      return this.families;
    }

    return this.families.filter((family) => family.family_name === this.selectedFamily);
  }

  // ==========================================================
  // PORTFOLIOS
  // ==========================================================

  get portfolioGroups(): {
    family_name: string;
    asset_class: string;
    portfolio: string;
    assets: any[];
  }[] {
    const groups: {
      family_name: string;
      asset_class: string;
      portfolio: string;
      assets: any[];
    }[] = [];

    for (const family of this.filteredFamilies) {
      for (const assetClass of family.asset_classes) {
        // --------------------------------------------------
        // Asset Class filter
        // --------------------------------------------------

        if (this.selectedAssetClass && assetClass.asset_class !== this.selectedAssetClass) {
          continue;
        }

        for (const portfolio of assetClass.portfolios) {
          groups.push({
            family_name: family.family_name,

            asset_class: assetClass.asset_class,

            portfolio: portfolio.portfolio,

            assets: portfolio.assets,
          });
        }
      }
    }

    return groups;
  }

  // ==========================================================
  // TOTAL PORTFOLIOS
  // ==========================================================

  get portfolioCount(): number {
    return this.portfolioGroups.length;
  }

  // ==========================================================
  // TOTAL ASSETS
  // ==========================================================

  getAssetCount(portfolio: { assets: any[] }): number {
    return portfolio.assets?.length ?? 0;
  }

  // ==========================================================
  // TOGGLE PORTFOLIO
  // ==========================================================

  togglePortfolio(portfolioKey: string): void {
    if (this.expandedPortfolio === portfolioKey) {
      this.expandedPortfolio = null;
    } else {
      this.expandedPortfolio = portfolioKey;
    }
  }

  // ==========================================================
  // PORTFOLIO KEY
  // ==========================================================

  getPortfolioKey(familyName: string, assetClass: string, portfolioName: string): string {
    return [familyName, assetClass, portfolioName].join('|');
  }
}
