// OAuth destinations are restricted even if a local response is malformed.
export function openGoogleAuthorization(value:string){
 const url=new URL(value);
 if(url.origin!=='https://accounts.google.com'||url.pathname!=='/o/oauth2/v2/auth'||url.username||url.password)throw new Error('Google returned an unexpected sign-in destination.');
 window.location.assign(url.href);
}
