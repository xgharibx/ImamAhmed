const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const path=require('node:path');
const base=process.env.PREVIEW_URL||'http://127.0.0.1:4174';
const out=path.join(__dirname,'artifacts');
(async()=>{
    await fs.mkdir(out,{recursive:true});
    const browser=await chromium.launch({headless:true,channel:'chrome'});
    try {
        for(const [name,width,height] of [['phone',390,844],['small-phone',320,740],['tablet',820,1180],['landscape-tablet',1180,820],['tablet-boundary',1200,820],['desktop-boundary',1201,900],['desktop',1440,1000]]){
            const context=await browser.newContext({viewport:{width,height},isMobile:width<=1200,hasTouch:width<=1200});
            const page=await context.newPage();
            page.setDefaultNavigationTimeout(60000);
            const errors=[];page.on('pageerror',error=>errors.push(error.message));
            await page.goto(base+'/',{waitUntil:'domcontentloaded'});
            await page.locator('#preloader').waitFor({state:'hidden'});
            await page.waitForFunction(()=>['.hero-title','.hero-buttons'].every(selector=>{
                const element=document.querySelector(selector);
                return !element||Number(getComputedStyle(element).opacity)>=0.99;
            }));
            await page.evaluate(async()=>{
                await document.fonts.ready;
                const animations=document.querySelector('.hero-content').getAnimations({subtree:true});
                await Promise.all(animations.filter(animation=>animation.effect.getTiming().iterations!==Infinity).map(animation=>animation.finished.catch(()=>{})));
            });
            assert.equal(new URL(page.url()).pathname,'/','Original homepage redirected');
            assert.equal(await page.locator('.hero-title').count(),1,'Original hero missing');
            assert.equal(await page.locator('.featured-grid').count(),1,'Original content layout missing');
            assert.equal(await page.locator('.welcome,.app-nav').count(),0,'Withdrawn design remains');
            const nav=page.locator('.mobile-bottom-nav');
            if(width<=1200){
                await nav.waitFor({state:'visible'});
                assert.equal(await page.locator('.hamburger').isVisible(),false,'Top hamburger still visible');
                assert.equal(await page.locator('#header .nav-menu').isVisible(),false,'Duplicate top menu still available');
                assert.equal(await page.locator('#header .logo').isVisible(),true,'Header branding missing');
                assert.equal(await nav.locator('a,button').count(),5);
                assert.equal(await nav.locator('[aria-current=page]').getAttribute('data-mobile-tab'),'home');
                const rect=await nav.boundingBox();
                assert.ok(rect.x>0&&rect.x+rect.width<width,'Navigation is not floating');
                assert.ok(rect.y+rect.height<height,'Navigation touches bottom edge');
                assert.equal(rect.height,54,'Navigation is no longer compact');
                assert.ok(rect.width<=328,'Navigation is too spread out');
                const track=await nav.locator('.mobile-nav-track').boundingBox();
                const more=await nav.locator('[data-mobile-tab=more]').boundingBox();
                assert.ok(more.x+more.width<track.x,'More button is not detached from the pill');
                assert.ok(await nav.locator('a,button').evaluateAll(elements=>elements.every(element=>{
                    const rect=element.getBoundingClientRect();
                    const label=element.querySelector('span');
                    return rect.width>=44&&rect.height>=44&&(!label||label.scrollWidth<=rect.width);
                })),'Touch targets or labels do not fit');
                let navigations=0;
                const onNavigation=frame=>{if(frame===page.mainFrame()) navigations++;};
                page.on('framenavigated',onNavigation);
                await page.evaluate(()=>window.scrollTo({top:200,behavior:'instant'}));
                await page.waitForFunction(()=>scrollY>100);
                await nav.locator('[data-mobile-tab=home]').click();
                await page.waitForFunction(()=>scrollY===0);
                assert.equal(navigations,0,'Tapping the current tab reloaded the page');
                page.off('framenavigated',onNavigation);
                await page.screenshot({path:path.join(out,name+'-original-home.png')});
                await nav.screenshot({path:path.join(out,name+'-premium-nav.png')});
                await nav.locator('[data-mobile-tab=more]').click();
                const sheet=page.locator('#mobile-nav-sheet');
                await sheet.waitFor({state:'visible'});
                assert.equal(await sheet.locator('a').count(),10);
                const last=sheet.locator('a').last();
                await last.scrollIntoViewIfNeeded();
                assert.ok(await last.isVisible());
                await page.screenshot({path:path.join(out,name+'-more.png')});
                await page.goBack();
                await sheet.waitFor({state:'hidden'});
                assert.equal(new URL(page.url()).pathname,'/');
                await nav.locator('[data-mobile-tab=more]').click();
                await sheet.getByRole('link',{name:'الأذكار',exact:true}).click();
                await page.waitForURL('**/adhkar.html');
                await page.goBack();
                await page.waitForURL(base+'/');
                await nav.locator('[data-mobile-tab=videos]').click();
                await page.waitForURL('**/videos.html');
                assert.equal(await nav.locator('[aria-current=page]').getAttribute('data-mobile-tab'),'videos');
                await page.goto(base+'/books/al-azhar.html',{waitUntil:'domcontentloaded'});
                if(await page.locator('#preloader').count()) await page.locator('#preloader').waitFor({state:'hidden'});
                assert.equal(await nav.locator('[aria-current=page]').getAttribute('data-mobile-tab'),'library');
                assert.equal(await page.locator('.book-container').count(),1);
                await page.screenshot({path:path.join(out,name+'-original-reader.png')});
            }else{
                assert.equal(await nav.isVisible(),false,'Mobile navigation visible on desktop');
                assert.equal(await page.locator('#header .nav-menu').isVisible(),true,'Desktop navigation was hidden');
                await page.screenshot({path:path.join(out,name+'-original-home.png')});
            }
            if(width<=1200) assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'Horizontal overflow');
            assert.deepEqual(errors,[]);
            console.log('PASS '+name+': original design, navigation, more menu, back behavior');
            await context.close();
        }
    }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
