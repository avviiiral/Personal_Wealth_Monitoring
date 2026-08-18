import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ChangeDetectorRef, Component, OnDestroy, OnInit, inject } from '@angular/core';
import { Subscription, timer } from 'rxjs';

import {
  AssetClassNode,
  FamilyNode,
  PortfolioNode,
  SubClassNode,
  PortfolioApiService,
} from '../../core/services/portfolio-api.service';

interface PortfolioGroup {
  family_name: string;
  portfolio: string;
  asset_classes: AssetClassNode[];
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
  private readonly cdr = inject(ChangeDetectorRef);

  private refreshSubscription: Subscription | null = null;

  families: FamilyNode[] = [];

  selectedFamily = '';
  selectedPortfolio = '';
  selectedAssetClass = '';
  selectedSubClass = '';

  expandedPortfolio: string | null = null;
  expandedAssetClass: string | null = null;
  expandedSubClass: string | null = null;

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

  get selectedFamilyData(): FamilyNode | null {
    if (!this.selectedFamily) {
      return null;
    }

    return this.families.find((family) => family.family_name === this.selectedFamily) ?? null;
  }

  get portfolioOptions(): PortfolioNode[] {
    const portfolios: PortfolioNode[] = [];

    for (const family of this.filteredFamilies) {
      portfolios.push(...family.portfolios);
    }

    return this.uniquePortfolios(portfolios);
  }

  get availableAssetClasses(): AssetClassNode[] {
    const map = new Map<string, AssetClassNode>();

    for (const portfolio of this.portfolioOptions) {
      for (const assetClass of portfolio.asset_classes) {
        if (!map.has(assetClass.asset_class)) {
          map.set(assetClass.asset_class, assetClass);
        }
      }
    }

    return Array.from(map.values()).sort((a, b) => a.asset_class.localeCompare(b.asset_class));
  }

  get availableSubClasses(): SubClassNode[] {
    const map = new Map<string, SubClassNode>();

    for (const assetClass of this.filteredAssetClasses) {
      for (const subClass of assetClass.sub_classes) {
        if (!map.has(subClass.sub_class)) {
          map.set(subClass.sub_class, subClass);
        }
      }
    }

    return Array.from(map.values()).sort((a, b) => a.sub_class.localeCompare(b.sub_class));
  }

  get filteredFamilies(): FamilyNode[] {
    if (!this.selectedFamily) {
      return this.families;
    }

    return this.families.filter((family) => family.family_name === this.selectedFamily);
  }

  get filteredPortfolios(): PortfolioNode[] {
    let portfolios = this.portfolioOptions;

    if (this.selectedPortfolio) {
      portfolios = portfolios.filter((portfolio) => portfolio.portfolio === this.selectedPortfolio);
    }

    return portfolios;
  }

  get filteredAssetClasses(): AssetClassNode[] {
    const map = new Map<string, AssetClassNode>();

    for (const portfolio of this.filteredPortfolios) {
      for (const assetClass of portfolio.asset_classes) {
        if (this.selectedAssetClass && assetClass.asset_class !== this.selectedAssetClass) {
          continue;
        }

        map.set(assetClass.asset_class, assetClass);
      }
    }

    return Array.from(map.values());
  }

  get portfolioGroups(): PortfolioGroup[] {
    const groups: PortfolioGroup[] = [];

    for (const family of this.filteredFamilies) {
      for (const portfolio of family.portfolios) {
        if (this.selectedPortfolio && portfolio.portfolio !== this.selectedPortfolio) {
          continue;
        }

        const assetClasses = portfolio.asset_classes.filter((assetClass) => {
          if (this.selectedAssetClass && assetClass.asset_class !== this.selectedAssetClass) {
            return false;
          }

          return true;
        });

        if (!assetClasses.length) {
          continue;
        }

        groups.push({
          family_name: family.family_name,
          portfolio: portfolio.portfolio,
          asset_classes: assetClasses,
        });
      }
    }

    return groups;
  }

  get portfolioCount(): number {
    return this.portfolioGroups.length;
  }

  getGroupAssetCount(group: PortfolioGroup): number {
    let count = 0;

    for (const assetClass of group.asset_classes) {
      for (const subClass of assetClass.sub_classes) {
        if (this.selectedSubClass && subClass.sub_class !== this.selectedSubClass) {
          continue;
        }

        count += subClass.assets.length;
      }
    }

    return count;
  }

  getAssetCount(portfolio: PortfolioNode): number {
    let count = 0;

    for (const assetClass of portfolio.asset_classes) {
      if (this.selectedAssetClass && assetClass.asset_class !== this.selectedAssetClass) {
        continue;
      }

      for (const subClass of assetClass.sub_classes) {
        if (this.selectedSubClass && subClass.sub_class !== this.selectedSubClass) {
          continue;
        }

        count += subClass.assets.length;
      }
    }

    return count;
  }

  getSubClassAssets(subClass: SubClassNode) {
    if (!this.selectedSubClass) {
      return subClass.assets;
    }

    if (subClass.sub_class !== this.selectedSubClass) {
      return [];
    }

    return subClass.assets;
  }

  selectFamily(familyName: string): void {
    this.selectedFamily = this.selectedFamily === familyName ? '' : familyName;

    this.selectedPortfolio = '';
    this.selectedAssetClass = '';
    this.selectedSubClass = '';

    this.clearExpansion();
  }

  selectPortfolio(portfolioName: string): void {
    this.selectedPortfolio = this.selectedPortfolio === portfolioName ? '' : portfolioName;

    this.selectedAssetClass = '';
    this.selectedSubClass = '';

    this.clearExpansion();
  }

  selectAssetClass(assetClass: string): void {
    this.selectedAssetClass = this.selectedAssetClass === assetClass ? '' : assetClass;

    this.selectedSubClass = '';

    this.clearExpansion();
  }

  selectSubClass(subClass: string): void {
    this.selectedSubClass = this.selectedSubClass === subClass ? '' : subClass;

    this.clearExpansion();
  }

  clearFamily(): void {
    this.selectedFamily = '';
    this.selectedPortfolio = '';
    this.selectedAssetClass = '';
    this.selectedSubClass = '';

    this.clearExpansion();
  }

  clearPortfolio(): void {
    this.selectedPortfolio = '';
    this.selectedAssetClass = '';
    this.selectedSubClass = '';

    this.clearExpansion();
  }

  clearAssetClass(): void {
    this.selectedAssetClass = '';
    this.selectedSubClass = '';

    this.clearExpansion();
  }

  clearSubClass(): void {
    this.selectedSubClass = '';

    this.clearExpansion();
  }

  togglePortfolio(portfolioKey: string): void {
    this.expandedPortfolio = this.expandedPortfolio === portfolioKey ? null : portfolioKey;
  }

  toggleAssetClass(assetClassKey: string): void {
    this.expandedAssetClass = this.expandedAssetClass === assetClassKey ? null : assetClassKey;
  }

  toggleSubClass(subClassKey: string): void {
    this.expandedSubClass = this.expandedSubClass === subClassKey ? null : subClassKey;
  }

  getPortfolioKey(familyName: string, portfolioName: string): string {
    return [familyName, portfolioName].join('|');
  }

  getAssetClassKey(familyName: string, portfolioName: string, assetClass: string): string {
    return [familyName, portfolioName, assetClass].join('|');
  }

  getSubClassKey(
    familyName: string,
    portfolioName: string,
    assetClass: string,
    subClass: string,
  ): string {
    return [familyName, portfolioName, assetClass, subClass].join('|');
  }

  private clearExpansion(): void {
    this.expandedPortfolio = null;
    this.expandedAssetClass = null;
    this.expandedSubClass = null;
  }

  private validateSelections(): void {
    if (this.selectedFamily && !this.familyOptions.includes(this.selectedFamily)) {
      this.selectedFamily = '';
    }

    if (
      this.selectedPortfolio &&
      !this.portfolioOptions.some((portfolio) => portfolio.portfolio === this.selectedPortfolio)
    ) {
      this.selectedPortfolio = '';
    }

    if (
      this.selectedAssetClass &&
      !this.availableAssetClasses.some(
        (assetClass) => assetClass.asset_class === this.selectedAssetClass,
      )
    ) {
      this.selectedAssetClass = '';
    }

    if (
      this.selectedSubClass &&
      !this.availableSubClasses.some((subClass) => subClass.sub_class === this.selectedSubClass)
    ) {
      this.selectedSubClass = '';
    }
  }

  private uniquePortfolios(portfolios: PortfolioNode[]): PortfolioNode[] {
    const map = new Map<string, PortfolioNode>();

    for (const portfolio of portfolios) {
      if (!map.has(portfolio.portfolio)) {
        map.set(portfolio.portfolio, portfolio);
      }
    }

    return Array.from(map.values()).sort((a, b) => a.portfolio.localeCompare(b.portfolio));
  }
}
