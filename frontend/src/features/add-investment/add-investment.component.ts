import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

import {
  PortfolioApiService,
  CreateAssetRequest,
  CreateTransactionRequest,
} from '../../core/services/portfolio-api.service';

@Component({
  selector: 'app-add-investment',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './add-investment.component.html',
  styleUrl: './add-investment.component.scss',
})
export class AddInvestmentComponent implements OnInit {
  private readonly portfolioApi = inject(PortfolioApiService);
  private readonly router = inject(Router);
  private readonly cdr = inject(ChangeDetectorRef);

  saving = false;
  error = '';
  success = '';

  asset = {
    name: '',
    category: 'STOCK',
    symbol: '',
    isin: '',
    institution: '',
    currency: 'INR',
  };

  transaction = {
    transaction_type: 'BUY',
    transaction_date: '',
    quantity: 0,
    price_per_unit: 0,
    amount: 0,
    fees: 0,
    notes: '',
  };

  readonly assetCategories = [
    { value: 'STOCK', label: 'Stock' },
    { value: 'MUTUAL_FUND', label: 'Mutual Fund' },
    { value: 'ETF', label: 'ETF' },
    { value: 'FIXED_DEPOSIT', label: 'Fixed Deposit' },
    { value: 'GOLD', label: 'Gold' },
    { value: 'CASH', label: 'Cash' },
    { value: 'REAL_ESTATE', label: 'Real Estate' },
    { value: 'BOND', label: 'Bond' },
    { value: 'CRYPTO', label: 'Cryptocurrency' },
    { value: 'OTHER', label: 'Other' },
  ];

  readonly transactionTypes = [
    { value: 'BUY', label: 'Buy' },
    { value: 'SELL', label: 'Sell' },
    { value: 'SIP', label: 'SIP' },
    { value: 'DIVIDEND', label: 'Dividend' },
    { value: 'INTEREST', label: 'Interest' },
    { value: 'DEPOSIT', label: 'Deposit' },
    { value: 'WITHDRAWAL', label: 'Withdrawal' },
    { value: 'BONUS', label: 'Bonus' },
    { value: 'SPLIT', label: 'Split' },
    { value: 'OTHER', label: 'Other' },
  ];

  ngOnInit(): void {
    const today = new Date();

    const year = today.getFullYear();
    const month = String(today.getMonth() + 1).padStart(2, '0');
    const day = String(today.getDate()).padStart(2, '0');

    this.transaction.transaction_date = `${year}-${month}-${day}`;

    this.calculateAmount();
  }

  calculateAmount(): void {
    const quantity = Number(this.transaction.quantity) || 0;
    const price = Number(this.transaction.price_per_unit) || 0;

    this.transaction.amount = Number((quantity * price).toFixed(2));
  }

  addInvestment(): void {
    if (this.saving) {
      return;
    }

    this.error = '';
    this.success = '';

    if (!this.asset.name.trim()) {
      this.error = 'Investment name is required.';
      return;
    }

    if (!this.asset.category) {
      this.error = 'Please select an asset type.';
      return;
    }

    if (!this.transaction.transaction_date) {
      this.error = 'Transaction date is required.';
      return;
    }

    if (Number(this.transaction.quantity) < 0) {
      this.error = 'Quantity cannot be negative.';
      return;
    }

    if (Number(this.transaction.price_per_unit) < 0) {
      this.error = 'Price per unit cannot be negative.';
      return;
    }

    if (Number(this.transaction.amount) < 0) {
      this.error = 'Amount cannot be negative.';
      return;
    }

    if (Number(this.transaction.fees) < 0) {
      this.error = 'Fees cannot be negative.';
      return;
    }

    this.saving = true;

    const assetPayload: CreateAssetRequest = {
      name: this.asset.name.trim(),
      category: this.asset.category,
      symbol: this.asset.symbol.trim() || null,
      isin: this.asset.isin.trim() || null,
      institution: this.asset.institution.trim() || null,
      currency: this.asset.currency,
    };

    this.portfolioApi.createAsset(assetPayload).subscribe({
      next: (createdAsset) => {
        const transactionPayload: CreateTransactionRequest = {
          asset: createdAsset.id,
          transaction_type: this.transaction.transaction_type,
          transaction_date: this.transaction.transaction_date,
          quantity: Number(this.transaction.quantity),
          price_per_unit: Number(this.transaction.price_per_unit),
          amount: Number(this.transaction.amount),
          fees: Number(this.transaction.fees) || 0,
          notes: this.transaction.notes.trim() || null,
        };

        this.portfolioApi.createTransaction(transactionPayload).subscribe({
          next: () => {
            this.saving = false;
            this.success = 'Investment added successfully.';
            this.cdr.detectChanges();

            setTimeout(() => {
              this.router.navigate(['/portfolio']);
            }, 800);
          },

          error: (error) => {
            console.error('Transaction creation error:', error);

            this.saving = false;

            this.error =
              error?.error?.detail ||
              error?.error?.amount?.[0] ||
              error?.error?.transaction_type?.[0] ||
              'Investment was created, but the transaction could not be created.';

            this.cdr.detectChanges();
          },
        });
      },

      error: (error) => {
        console.error('Asset creation error:', error);

        this.saving = false;

        this.error =
          error?.error?.detail ||
          error?.error?.name?.[0] ||
          error?.error?.category?.[0] ||
          'Unable to create investment.';

        this.cdr.detectChanges();
      },
    });
  }

  cancel(): void {
    this.router.navigate(['/portfolio']);
  }
}
