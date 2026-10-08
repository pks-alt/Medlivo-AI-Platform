import { teamApi } from '@/lib/team/runtime';
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export const GET = teamApi;
export const POST = teamApi;
export const PATCH = teamApi;
export const PUT = teamApi;
// No generic DELETE proxy; the private API still enforces route-level authorization.
