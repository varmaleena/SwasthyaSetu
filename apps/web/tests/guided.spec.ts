import {test,expect} from '@playwright/test';

test('plain-language story saves approvals, partial delivery and completed receipt',async({page})=>{
  await page.goto('/');
  await expect(page.getByRole('heading',{name:/One centre is running low/})).toBeVisible();
  await page.screenshot({path:'../../docs/screenshots/guided-welcome.png',fullPage:true});
  await page.getByRole('button',{name:/Try the 3-minute story/}).click();
  await expect(page.getByLabel('Tablets counted')).toHaveValue('40');
  await expect(page.getByLabel('Simulated role')).toHaveCount(0);
  await page.getByRole('button',{name:/Save Anitha’s stock count/}).click();
  await page.getByRole('button',{name:/Find a centre that can help/}).click();
  await expect(page.getByRole('heading',{name:'Anandapur can share 60 tablets.'})).toBeVisible();
  await page.screenshot({path:'../../docs/screenshots/guided-request.png',fullPage:true});
  await page.getByRole('button',{name:/Request these 60 tablets/}).click();
  await page.getByRole('button',{name:/Approve as Dr Kavya Rao/}).click();
  await page.getByRole('button',{name:/Approve as Dr Imran Ali/}).click();
  await page.getByRole('button',{name:/Record the box leaving Anandapur/}).click();
  await page.getByRole('button',{name:'Try a partial delivery: only 20 arrived'}).click();
  await page.getByRole('button',{name:/Confirm 20 tablets received/}).click();
  await expect(page.getByRole('heading',{name:'Anitha checks the remaining tablets.'})).toBeVisible();
  await page.getByRole('button',{name:'All 40 arrived'}).click();
  await page.getByRole('button',{name:/Confirm 40 tablets received/}).click();
  await expect(page.getByRole('heading',{name:'60 tablets received and accounted for.'})).toBeVisible();
  await page.reload();
  await expect(page.getByRole('heading',{name:'60 tablets received and accounted for.'})).toBeVisible();
  await page.screenshot({path:'../../docs/screenshots/guided-delivered.png',fullPage:true});
});

test('phone story explains people and responds to changed stock',async({page})=>{
  await page.setViewportSize({width:390,height:844});await page.goto('/');
  await page.getByRole('button',{name:/Try the 3-minute story/}).click();
  await page.getByRole('button',{name:'Meet the team',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Who does what?'})).toBeVisible();
  await page.getByLabel('Tablets counted').fill('80');
  await page.getByRole('button',{name:/Save Anitha’s stock count/}).click();
  await page.getByRole('button',{name:/Find a centre that can help/}).click();
  await expect(page.getByRole('heading',{name:'Anandapur can share 20 tablets.'})).toBeVisible();
  await page.screenshot({path:'../../docs/screenshots/guided-mobile.png',fullPage:true});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
});
