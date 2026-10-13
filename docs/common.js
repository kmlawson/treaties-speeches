(function(){var r=document.documentElement,k='ts-theme',f='ts-font';
try{var t=localStorage.getItem(k);if(t)r.setAttribute('data-theme',t);var z=localStorage.getItem(f);if(z)r.style.fontSize=z+'%'}catch(e){}
window.addEventListener('DOMContentLoaded',function(){
var b=document.getElementById('themeBtn');if(b)b.onclick=function(){var d=r.getAttribute('data-theme')=='dark'?'light':'dark';r.setAttribute('data-theme',d);try{localStorage.setItem(k,d)}catch(e){}};
function fs(d){var c=parseInt(r.style.fontSize)||100;c=Math.max(80,Math.min(150,c+d));r.style.fontSize=c+'%';try{localStorage.setItem(f,c)}catch(e){}}
var p=document.getElementById('fontUp'),m=document.getElementById('fontDown');if(p)p.onclick=function(){fs(10)};if(m)m.onclick=function(){fs(-10)};
var top=document.getElementById('backToTop');if(top){window.addEventListener('scroll',function(){top.classList.toggle('visible',window.scrollY>400)});top.onclick=function(){window.scrollTo({top:0,behavior:'smooth'})}}
var mo=document.getElementById('aboutModal'),na=document.getElementById('navAbout');
if(mo&&na){na.onclick=function(e){e.preventDefault();mo.classList.add('open')};mo.onclick=function(e){if(e.target==mo||e.target.id=='aboutClose')mo.classList.remove('open')};
document.addEventListener('keydown',function(e){if(e.key=='Escape')mo.classList.remove('open')})}
});})();