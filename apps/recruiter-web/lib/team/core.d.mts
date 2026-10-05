export const SESSION_COOKIE: string;
export const LOGIN_COOKIE: string;
export class SafeError extends Error { status:number; constructor(status:number,message:string); }
export function securityHeaders(extra?: Record<string,string>): Record<string,string>;
export function validateConfig(env: NodeJS.ProcessEnv): null | {origin:string;apiUrl:string;clientId:string;clientSecret:string;domain:string;encryptionKey:Buffer;databaseUrl:string;sessionSeconds:number;idleSeconds:number};
export function createGateway(options: {config: NonNullable<ReturnType<typeof validateConfig>>;store:unknown;verifyIdToken:unknown;api:unknown}): (request:Request)=>Promise<Response>;
