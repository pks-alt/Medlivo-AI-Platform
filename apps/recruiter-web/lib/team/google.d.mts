export function googleVerifier(clientId:string,domain:string): (token:string,nonce:string)=>Promise<{sub:string;exp:number}>;
