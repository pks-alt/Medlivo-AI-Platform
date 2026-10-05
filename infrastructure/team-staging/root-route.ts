// Only present in the isolated staging image, not in the existing application.
export const dynamic = 'force-dynamic';
export function GET() {
  return new Response(null, { status: 303, headers: {
    Location: '/team', 'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer'
  }});
}
