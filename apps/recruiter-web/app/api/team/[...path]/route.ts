import { teamApi } from '@/lib/team/runtime';
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export const GET = teamApi;
export const POST = teamApi;
export const PATCH = teamApi;
// No generic DELETE/PUT proxy; only allowlisted operations are exposed.
