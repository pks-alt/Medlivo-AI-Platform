export function createPrivateApi(url:string): (token:string,path:string,options?:unknown)=>Promise<Response>;
