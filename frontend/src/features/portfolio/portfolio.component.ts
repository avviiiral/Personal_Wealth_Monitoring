PS D:\PWMS> cd .\frontend\
PS D:\PWMS\frontend> ng serve
Application bundle generation failed. [10.634 seconds] - 2026-08-17T11:30:42.074Z

▲ [WARNING] NG8113: All imports are unused [plugin angular-compiler]

    src/app/layout/sidebar/sidebar.component.ts:18:2:
      18 │   imports: [
         ╵   ~~~~~~~


X [ERROR] NG5002: Unexpected closing tag "nav". It may happen when the tag has already been closed by another tag. For more info see https://www.w3.org/TR/html5/syntax.html#closing-elements-that-have-implied-end-tags [plugin angular-compiler]

    src/app/layout/sidebar/sidebar.component.html:79:2:
      79 │   </nav>
         ╵   ~~~~~~

  Error occurs in the template of component SidebarComponent.

    src/app/layout/sidebar/sidebar.component.ts:30:15:
      30 │   templateUrl: './sidebar.component.html',
         ╵                ~~~~~~~~~~~~~~~~~~~~~~~~~~


X [ERROR] TS1005: ',' expected. [plugin angular-compiler]

    src/features/portfolio/portfolio.component.ts:2:20:
      2 │ import { Chanimport { CommonModule } from '@angular/common';
        ╵                     ^


X [ERROR] TS1141: String literal expected. [plugin angular-compiler]

    src/features/portfolio/portfolio.component.ts:2:20:
      2 │ import { Chanimport { CommonModule } from '@angular/common';
        ╵                     ~~~~~~~~~~~~~~~~


X [ERROR] TS1005: ';' expected. [plugin angular-compiler]

    src/features/portfolio/portfolio.component.ts:2:37:
      2 │ import { Chanimport { CommonModule } from '@angular/common';
        ╵                                      ~~~~


X [ERROR] TS2304: Cannot find name 'from'. [plugin angular-compiler]

    src/features/portfolio/portfolio.component.ts:2:37:
      2 │ import { Chanimport { CommonModule } from '@angular/common';
        ╵                                      ~~~~


X [ERROR] TS2304: Cannot find name 'geDetectorRef'. [plugin angular-compiler]

    src/features/portfolio/portfolio.component.ts:3:45:
      3 │ ...e } from '@angular/forms';geDetectorRef, Component, OnInit, inje...
        ╵                              ~~~~~~~~~~~~~


X [ERROR] TS2695: Left side of comma operator is unused and has no side effects. [plugin angular-compiler]

    src/features/portfolio/portfolio.component.ts:3:45:
      3 │ ...e } from '@angular/forms';geDetectorRef, Component, OnInit, inje...
        ╵                              ~~~~~~~~~~~~~


X [ERROR] TS2695: Left side of comma operator is unused and has no side effects. [plugin angular-compiler]

    src/features/portfolio/portfolio.component.ts:3:45:
      3 │ ...om '@angular/forms';geDetectorRef, Component, OnInit, inject } f...
        ╵                        ~~~~~~~~~~~~~~~~~~~~~~~~


X [ERROR] TS2695: Left side of comma operator is unused and has no side effects. [plugin angular-compiler]

    src/features/portfolio/portfolio.component.ts:3:45:
      3 │ ...@angular/forms';geDetectorRef, Component, OnInit, inject } from ...
        ╵                    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


X [ERROR] TS2304: Cannot find name 'Component'. [plugin angular-compiler]

    src/features/portfolio/portfolio.component.ts:3:60:
      3 │ ...gular/forms';geDetectorRef, Component, OnInit, inject } from '@a...
        ╵                                ~~~~~~~~~


X [ERROR] TS2304: Cannot find name 'OnInit'. [plugin angular-compiler]

    src/features/portfolio/portfolio.component.ts:3:71:
      3 │ ...s';geDetectorRef, Component, OnInit, inject } from '@angular/core';
        ╵                                 ~~~~~~


X [ERROR] TS2304: Cannot find name 'inject'. [plugin angular-compiler]

    src/features/portfolio/portfolio.component.ts:3:79:
      3 │ ...s';geDetectorRef, Component, OnInit, inject } from '@angular/core';
        ╵                                         ~~~~~~


X [ERROR] TS1128: Declaration or statement expected. [plugin angular-compiler]

    src/features/portfolio/portfolio.component.ts:3:86:
      3 │ ...s';geDetectorRef, Component, OnInit, inject } from '@angular/core';
        ╵                                                ^


X [ERROR] TS1434: Unexpected keyword or identifier. [plugin angular-compiler]

    src/features/portfolio/portfolio.component.ts:3:88:
      3 │ ...s';geDetectorRef, Component, OnInit, inject } from '@angular/core';
        ╵                                                  ~~~~


X [ERROR] TS2304: Cannot find name 'from'. [plugin angular-compiler]

    src/features/portfolio/portfolio.component.ts:3:88:
      3 │ ...s';geDetectorRef, Component, OnInit, inject } from '@angular/core';
        ╵                                                  ~~~~


X [ERROR] TS2304: Cannot find name 'Component'. [plugin angular-compiler]

    src/features/portfolio/portfolio.component.ts:7:1:
      7 │ @Component({
        ╵  ~~~~~~~~~


X [ERROR] TS2304: Cannot find name 'CommonModule'. [plugin angular-compiler]

    src/features/portfolio/portfolio.component.ts:11:4:
      11 │     CommonModule,
         ╵     ~~~~~~~~~~~~


X [ERROR] TS2304: Cannot find name 'OnInit'. [plugin angular-compiler]

    src/features/portfolio/portfolio.component.ts:17:43:
      17 │ export class PortfolioComponent implements OnInit {
         ╵                                            ~~~~~~


X [ERROR] TS2304: Cannot find name 'inject'. [plugin angular-compiler]

    src/features/portfolio/portfolio.component.ts:18:34:
      18 │   private readonly portfolioApi = inject(PortfolioApiService);
         ╵                                   ~~~~~~


X [ERROR] TS2304: Cannot find name 'inject'. [plugin angular-compiler]

    src/features/portfolio/portfolio.component.ts:20:25:
      20 │   private readonly cdr = inject(ChangeDetectorRef);
         ╵                          ~~~~~~


X [ERROR] TS2304: Cannot find name 'ChangeDetectorRef'. [plugin angular-compiler]

    src/features/portfolio/portfolio.component.ts:20:32:
      20 │   private readonly cdr = inject(ChangeDetectorRef);
         ╵                                 ~~~~~~~~~~~~~~~~~


X [ERROR] TS7006: Parameter 'response' implicitly has an 'any' type. [plugin angular-compiler]

    src/features/portfolio/portfolio.component.ts:41:13:
      41 │       next: (response) => {
         ╵              ~~~~~~~~


X [ERROR] TS7006: Parameter 'error' implicitly has an 'any' type. [plugin angular-compiler]

    src/features/portfolio/portfolio.component.ts:49:14:
      49 │       error: (error) => {
         ╵               ~~~~~


Watch mode enabled. Watching for file changes...
