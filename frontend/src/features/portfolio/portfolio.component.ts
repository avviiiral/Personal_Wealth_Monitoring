import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';

import { FamilyNode, PortfolioApiService } from '../../core/services/portfolio-api.service';

@Component({
  selector: 'app-portfolio',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './portfolio.component.html',
  styleUrl: './portfolio.component.scss',
})
export class PortfolioComponent implements OnInit {
  private readonly portfolioApi = inject(PortfolioApiService);

  private readonly cdr = inject(ChangeDetectorRef);

  families: FamilyNode[] = [];

  selectedFamily = '';
  selectedAssetClass = '';

  expandedPortfolio: string | null = null;

  loading = true;
  error = '';

  ngOnInit(): void {
    this.loadPortfolio();
  }

  loadPortfolio(): void {
    this.loading = true;
    this.error = '';

    this.portfolioApi.getPortfolioTree().subscribe({
      next: (response) => {
        this.families = response.results ?? [];

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

  get selectedFamilyData(): FamilyNode | null {
    if (!this.selectedFamily) {
      return null;
    }

    return this.families.find((family) => family.family_name === this.selectedFamily) ?? null;
  }

  get assetClasses() {
    return this.selectedFamilyData?.asset_classes ?? [];
  }

  get selectedAssetClassData() {
    if (!this.selectedAssetClass) {
      return this.assetClasses;
    }

    return this.assetClasses.filter((item) => item.asset_class === this.selectedAssetClass);
  }

  onFamilyChange(): void {
    this.selectedAssetClass = '';

    this.expandedPortfolio = null;
  }

  onAssetClassChange(): void {
    this.expandedPortfolio = null;
  }

  togglePortfolio(portfolioName: string): void {
    if (this.expandedPortfolio === portfolioName) {
      this.expandedPortfolio = null;
    } else {
      this.expandedPortfolio = portfolioName;
    }
  }
}
