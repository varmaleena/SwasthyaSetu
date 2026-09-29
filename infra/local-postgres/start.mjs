import EmbeddedPostgres from 'embedded-postgres';
import {existsSync} from 'node:fs';
import {resolve} from 'node:path';
const directory=resolve('../../tmp/postgres');
const pg=new EmbeddedPostgres({databaseDir:directory,user:'demo',password:'local-development-only',port:55432,persistent:true,createPostgresUser:false,postgresFlags:['-h','127.0.0.1'],onLog:()=>{},onError:console.error});
if(!existsSync(resolve(directory,'PG_VERSION')))await pg.initialise();
await pg.start();
const client=pg.getPgClient();await client.connect();
for(const name of ['state_a','state_b','test_a','test_b']){
 const result=await client.query('SELECT 1 FROM pg_database WHERE datname=$1',[name]);
 if(!result.rowCount)await client.query(`CREATE DATABASE ${name}`);
}
await client.end();console.log('Local PostgreSQL ready on 127.0.0.1:55432. Development credentials only.');
const finish=async()=>{await pg.stop();process.exit(0)};
process.on('SIGINT',finish);process.on('SIGTERM',finish);setInterval(()=>{},60000);
