# WareStock AI — Product Requirement Document

## Overview

This document details every feature planned and developed for the WareStock AI platform. Features marked as **✓ Developed** have been completed and merged. Features left blank are yet to be developed.

---

## Backend (FastAPI / PostgreSQL / SQLModel)

### Authentication & Authorization

| Issue | Feature | Status |
|---|---|---|
| #2 | Implement JWT authentication (RS256/HS256) | ✓ Developed |
| #47 | Fix ModuleNotFoundError: No module named 'asyncpg' | ✓ Developed |
| #55 | Implement persistent refresh token store | ✓ Developed |

### RBAC & Multi-Tenant

| Issue | Feature | Status |
|---|---|---|
| #1 | Implement multi-tenant database schema | ✓ Developed |
| #3 | Implement RBAC middleware | ✓ Developed |
| #4 | Implement SKU and Location CRUD | ✓ Developed |
| #5 | Implement stock movement tracking | ✓ Developed |
| #6 | Implement barcode scan API | ✓ Developed |
| #7 | Implement AI photo-count pipeline | ✓ Developed |
| #8 | Implement reorder alert system | |
| #9 | Implement discrepancy detection engine | |
| #10 | Implement audit log | |
| #11 | Implement platform management APIs | |
| #12 | Implement CSV export endpoint | |

### AI & Intelligence

| Issue | Feature | Status |
|---|---|---|
| #16 | Implement natural-language stock assistant | |

### Infrastructure & Monitoring

| Issue | Feature | Status |
|---|---|---|
| #13 | Set up Sentry error tracking | |
| #14 | Set up Prometheus metrics | |
| #15 | Implement rate limiting | |
| #52 | Bugfix: System audit and fixes — critical bugs, type safety, and consistency | ✓ Developed |

---

## Web Frontend (React 19 / Vite 6 / TailwindCSS v4)

### Auth & Layout

| Issue | Feature | Status |
|---|---|---|
| #27 | Implement web login page | |
| #28 | Implement web dashboard layout | |
| #29 | Implement web dashboard page | |

### Inventory Management

| Issue | Feature | Status |
|---|---|---|
| #30 | Implement SKU management page | |
| #31 | Implement location management page | |
| #32 | Implement stock movements page | |
| #33 | Implement alerts management page | |
| #34 | Implement discrepancy resolution page | |
| #35 | Implement web photo count page | |
| #39 | Implement CSV export functionality | |

### AI Features

| Issue | Feature | Status |
|---|---|---|
| #36 | Implement AI assistant page | |

### Platform Admin & User Management

| Issue | Feature | Status |
|---|---|---|
| #37 | Implement user management page | |
| #38 | Implement platform admin page | |

### UI Infrastructure

| Issue | Feature | Status |
|---|---|---|
| #40 | Implement form validation with react-hook-form | |
| #41 | Implement API client with axios | |
| #42 | Implement state management with Zustand | |
| #43 | Implement responsive design with TailwindCSS | |
| #44 | Implement data table with TanStack Table | |
| #45 | Implement Lighthouse CI | |

### Design

| Issue | Feature | Status |
|---|---|---|
| #60 | Design Template: WareStock AI Design System | |

---

## Mobile App (React Native / Expo SDK 57)

| Issue | Feature | Status |
|---|---|---|
| #17 | Implement mobile login screen | |
| #18 | Implement mobile tab navigation | |
| #19 | Implement barcode scanner screen | |
| #20 | Implement mobile dashboard screen | |
| #21 | Implement photo count screen | |
| #22 | Implement mobile alerts screen | |
| #23 | Implement mobile stock view screen | |
| #24 | Implement secure token storage | |
| #25 | Implement mobile API client | |
| #26 | Implement push notification handling | |

---

## Summary

### Developed Features (Closed Issues)

| Issue # | Feature |
|---|---|
| #1 | Implement multi-tenant database schema |
| #2 | Implement JWT authentication (RS256/HS256) |
| #3 | Implement RBAC middleware |
| #4 | Implement SKU and Location CRUD |
| #5 | Implement stock movement tracking |
| #6 | Implement barcode scan API |
| #7 | Implement AI photo-count pipeline |
| #47 | Fix ModuleNotFoundError: No module named 'asyncpg' |
| #52 | Bugfix: System audit and fixes — critical bugs, type safety, and consistency |
| #55 | Implement persistent refresh token store |

### Current Focus

| Issue # | Feature |
|---|---|
| **#8** | **Implement reorder alert system** |

### Undeveloped Features (Open Issues)

8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 60
