# English Video Learning - Frontend

Next.js 14 frontend application for the English Video Learning platform.

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **UI Components**: shadcn/ui (Radix UI primitives)
- **Form Handling**: React Hook Form + Zod
- **HTTP Client**: Axios
- **Icons**: Lucide React

## Getting Started

### Prerequisites

- Node.js 20+
- npm or pnpm

### Installation

1. Install dependencies:
```bash
npm install
```

2. Copy environment variables:
```bash
cp .env.example .env.local
```

3. Update the `.env.local` file with your backend API URL.

### Development

Run the development server:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Build

Create a production build:

```bash
npm run build
```

Start the production server:

```bash
npm start
```

### Docker Development

Build and run with Docker:

```bash
docker build -f Dockerfile.dev -t english-video-learning-frontend .
docker run -p 3000:3000 english-video-learning-frontend
```

## Project Structure

```
frontend/
├── src/
│   ├── app/              # App router pages
│   ├── components/       # React components
│   ├── lib/             # Utility functions
│   └── styles/          # Global styles
├── public/              # Static assets
└── ...config files
```

## Environment Variables

- `NEXT_PUBLIC_API_URL`: Backend API URL (default: http://localhost:5000)
- `NEXT_PUBLIC_APP_NAME`: Application name
- `NEXT_PUBLIC_APP_URL`: Frontend URL (default: http://localhost:3000)

## Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm start` - Start production server
- `npm run lint` - Run ESLint
- `npm run type-check` - Run TypeScript type checking
