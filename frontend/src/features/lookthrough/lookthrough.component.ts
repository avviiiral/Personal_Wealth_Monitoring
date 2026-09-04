import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';

import {
  MutualFundLookthroughAsset,
  MutualFundSchemeLookthroughResponse,
  MutualFundUnderlyingHoldingRow,
  MutualFundsApiService,
} from '../../core/services/mutual-funds-api.service';

/**
 * LOOK-THROUGH EXPOSURE
 *
 * Minimum UI for the Mutual Fund Underlying Holdings feature: pick
 * one held fund, see what it actually owns and this user's indirect
 * rupee exposure to each security - derived, not stored (see
 * mutual_funds/services/lookthrough_engine.py). No existing
 * mutual-fund transaction/SIP screens are touched by this page.
 */
@Component({
  selector: 'app-lookthrough',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './lookthrough.component.html',
  styleUrl: './lookthrough.component.scss',
})
export class LookthroughComponent implements OnInit {
  private readonly mutualFundsApi = inject(MutualFundsApiService);
  private readonly cdr = inject(ChangeDetectorRef);

  loadingFunds = true;
  fundsError = '';
  funds: MutualFundLookthroughAsset[] = [];

  selectedSchemeId: number | null = null;

  loadingLookthrough = false;
  lookthroughError = '';
  lookthrough: MutualFundSchemeLookthroughResponse | null = null;

  ngOnInit(): void {
    this.loadFunds();
  }

  private loadFunds(): void {
    this.loadingFunds = true;
    this.fundsError = '';

    this.mutualFundsApi.getLookthroughAssets().subscribe({
      next: (data) => {
        this.funds = data.results;
        this.loadingFunds = false;

        if (this.funds.length > 0) {
          this.selectScheme(this.funds[0].id);
        }

        this.cdr.markForCheck();
      },

      error: (error) => {
        console.error('LOOK-THROUGH FUNDS ERROR:', error);

        this.loadingFunds = false;
        this.fundsError = 'Unable to load your mutual fund holdings.';
        this.cdr.markForCheck();
      },
    });
  }

  onFundChange(schemeId: string): void {
    this.selectScheme(Number(schemeId));
  }

  private selectScheme(schemeId: number): void {
    this.selectedSchemeId = schemeId;
    this.lookthrough = null;
    this.lookthroughError = '';
    this.loadingLookthrough = true;

    this.mutualFundsApi.getSchemeLookthrough(schemeId).subscribe({
      next: (data) => {
        this.lookthrough = data;
        this.loadingLookthrough = false;
        this.cdr.markForCheck();
      },

      error: (error) => {
        console.error('LOOK-THROUGH DATA ERROR:', error);

        this.loadingLookthrough = false;
        this.lookthroughError = 'Unable to load look-through data for this fund.';
        this.cdr.markForCheck();
      },
    });
  }

  trackByIsin(_index: number, row: MutualFundUnderlyingHoldingRow): string {
    return row.isin ?? row.security;
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

  formatDate(value: string | null): string {
    if (!value) {
      return '-';
    }

    return new Date(value).toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  }
}
