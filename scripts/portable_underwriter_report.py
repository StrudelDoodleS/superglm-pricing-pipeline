# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "numpy",
#   "pandas",
#   "plotly>=6.9",
#   "pyarrow>=23.0.1",
# ]
# ///
"""Portable, prediction-only underwriter model review.

Copy this file anywhere and run it with ``uv run`` or import ``build_report``.
It contains the model-neutral report runtime and has no repository dependency.
"""

from __future__ import annotations

import argparse
import base64 as _base64
import sys as _sys
import tomllib
import types as _types
import zlib as _zlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd

SOURCE_SHA256 = "79773e2a0116ee98329329c3e332d75a23f3a59462c448ae38a9fc0fff61c753"
_RUNTIME_PREFIX = "_portable_underwriter_79773e2a0116"
# fmt: off
_EMBEDDED_SOURCES = {
    '_portable_underwriter_79773e2a0116.reporting._underwriter_styles': (
        'c-'
        'pmF>u%(>75?w1P;CV8q@$^%xvV`#iZ*GA7HH5SoBk*kLBNry8O9n(pfnfnBCpZM>BIC%dJZoVNl{~a<7N@B=L|)j'
        '>vt~HUSD7TiRP@NLA#^DH}BsEbibilMzesGg4VR8%t%qel0%tMe&Vd9Jow8G-'
        '~BD%w61tNyS~1@y88axfBgOXAAb7!kMF<z3HSLb;7DKds%nEzS3!_gMa9D=-'
        'O)W=2L;>i+6N$q;byxIZt{2eT}~vSCM7M9CjOJOmY!Q6#d$JM?j&h{XlVwt)pC`+TdBP&4m<)ei?VkaHHl%<@~Xt'
        'M?$Z0^z1nxn8SKHg8*&>jqG=E>?%~H0enhh*nWznl1F(D(-'
        'LLL5(v!lb%8{vTLrJdA;)10tP8Nweq2i?6;^UiqMWRF!pJ-83CzNrK&6m_98Zz9GI8wXhReER~9-'
        '1A=a1+7(Je~&g<upJcqFKCBtTzXqlN63W5`L>xYkviQZ`uMG%vZe)ILX+d37h>oSkz~Wwg(AUn%2~~MQp5+lw=*;'
        '*_8P@h!dN%08+OTE1R08E%?ZZW$kVq%vTY9_siAQm($?O^?F0|ic|3`$<YTt1)J&|HtZuqvnneC=^=n;cJ00pez#'
        '|(-'
        'Z6SmpLZ194^EGwFOaq&>Eo7H;NV(Oo9#p#y{WP%u}#LBx*$*MATQ|o;rV^D;|{3=9K8%7WcFY^@Icz8g8uWNX<7a'
        'hrd8R}5*|t6C*@)z!ndqcyVfMjgm_wa)sgaC_zpR=)dl8N#AzA^kf7!j9v9E+^Y7x>A_z%c7vKa>4e&S(zAjk#_#'
        'H{#i_d?CwbS7GJ>6C`_~&1*r$IwX@CwRVF4c2r+o}XIEx>kD0FC+p;jRv0<qlT1!XEZYp;E1_c_c;aWQ{<9lB8oH'
        'uFpYJ6)e*d3i_m9qMTDp+qv(=uOZv_N3{ifYkp08$4g{yeA@|1ECpWg&|v7Q#^M`F^CVvxt4P|iBONST(JY@E%fJ'
        'cArT}pM6r=~<AirhRh6HhgW)DFHVZ~Z-'
        '(rC6^8fsq)_y~`zVet4=3FT6S@m%7EmTVXR|M{!y==w+dTVciO(1OnZek6{K#8RPJwIr<ayrHdFDRlc`#~{^|KY}'
        '=2c$JuGe#7>dSx6~;X9hkBXb12pPOPhjwG5<!1XK`I+=CgQ2<b>r#sa(DVw@wkM_{*!FL<>prld%3W%LGNkSvVl&'
        'n?kWtKw3#y&-%W%tV-'
        '<Tm1AgG_i1_$A&GbJ71GHJF$)uo1+3k!YNq?V7$f)H}dHXZBLYzMi^}>@R$9CfYXQJ&L9~6iq2b=jbE^r3KBbed$'
        'C)CUwB?SYKBK_Oi4@t2~}{nkc;6s4r~l$zPv`m3z%E{A4!HTK!6J=qFk|soawM1Fgk{EHmlE^XhD8>Qkq#sf^#7z'
        'B-Fi<7y^m@>oykNj4ZkyYlgr=p)=YzJaIH7{<JXMwk_z(=e7EfbjNBL+WK)wPr<v-'
        '%>noK_v+DC1HWk{2JD3rKyBY<rGPUBXtc}08aQC!@qKoaySG(UfO11TMQpE=ixRu5CDiAf6@`RH{Dj5qBY-ZX0rb'
        '>wP==l!B7Z5`MF{VF@pFYh<$j}&pWP|j><Di)>iRIZV;GAl%ReGSZF2(v3QmuVo<c!{{SFOQ<T4FOp#t#G%_D0=&'
        'sV}4x<2&djABMw(Wxa}$e$<5fo-O>M`w)FR0<2eaoCr3A@(+<$v&Gr2OyTzz$eMfL@5M!>q}7XgTz*>tI-'
        'O*+GY*QsAvEbz}oOCHUx3tkAT)8*a|baoA_)Y7*Nq5^J14*?kre-QMR#8v{7OS&%utm9nmI<JV*4^$z^~az`C=1h'
        '@}G_J+SV>ZP^&U$P4=I@#lC2G4N%>o)^4Z9C6r#sh+}|lRXvjiWQjrC=Rs35>Z>UZN8Y5Uk)}Mq!HORk#k4T;5Ov'
        'k^hH@TTGXe$8&bXzwpG2h{X&v@SA+gKqjcfpv?Zdt70g*EC#(-0Cm?T(JK2RQ<g-2GH&`KeGs9IR3mF-AGBk}t;T'
        'b2CbZ!x~97K1G`8kvZYY>EMO4{3GiV6iTZ*g>y^U0(Ozon|NtwX#;l@(2^F>vd&_3JvWiH9kOE+@fmiYk2^&CP*j'
        '1_j3=BX>D-7B77Vi3!liQ3|NElUV*GYaCKOouHwm&lFmUuf)q&;_wCS8%CS{2!?K-`f=H1$z#{VxS8-;-'
        'HJrg*Bl<^qBV5Sv_}mxhhNS1wB;;qaCoLlw0;252V(c=-'
        'P`5H{&Z1j4O5?6efnoDG8!yt#1enFnN5DQ7#0aDqw<vq)h)9ll~*TVBEjT@#YP8Do_uZU4_k{^kG(Xz89M_0bE`-'
        'kvbI>630H2F49j2(^$dN4rNn)cl+mIkukyyBzxxjYYYzMfebQWaB*j4{4XHFpFS((!=Ob{bY~|^GMxs(BJ&|h19m'
        'L9CzHsol0y=;L*53KvTZN7i1*=BNU(lL&dVPLWAR;RE*LS`1+6?Rx2bksvOs=)i1?=bQz7%oM?ZNAn0}M9yRAq>p'
        'l%3YanXoD~_3AK+Z1;dhR#qc<f8}4io7+;E0?c)(pq^2Mi2($9g58Y|3Q{*z)OO-G(d*+=A+S>&K!BW`Y39vVgM-'
        '>#uYN_z><WA(EAWdoy-_-dZeJ)AY8ZV51p01SN(%i2q+l;EIQ1O0xEbJvlJ&Feobg5s8j5Tvlld*2Vscr~Tn!=jR'
        'Yt*R+da5J;~fa-'
        '!17_jTTHTtTo}^{?ZL_2cr(Nm;JuiK=!H|1G0xTnG4yJ4A?@UQ%4(o4PT0f+kh%tgPM5ZTETJf0hE0~gbHnqYtzz'
        'jTaE5h+8N8-'
        'ly^~Bku&uocvcV+c%Tw;!k@<?tUhw;%Yb><v!^<zHin)*Magx4lxmd<wR41yj4(?x)nAGj+<PG|RvDB__JnD++nc'
        'B1U_DU1M3!C-{uQ_#-'
        'DT2J$0xb$wH%v^+Pdl)(9980aIolk!#(J&W;Ec9}6_AAqmu9uDHHLOKwoq4^*7XM2fT9891iMw;mDehOlwrEebp7'
        '9d|L6KOU6U))hpNWg7}w1_gK4PD2Jsh(Kj<FTqCt>Bq#rH_`Y{yOO&Fq`-'
        '1^Sti{Q6`zHmWcRsf}MdZ4sQa5g;^X>sy-Q2eHzZ0kpK14*YK`GrqK7jIPh_TG-'
        'z*UZ&k1?mH~bk^x}jws%&;r*Qt6RTRuWsQ9j;f=#-'
        'j@=eTLqJsfJwFdiRH$6KjC$v2blF4S0C`3j@m}`!!64ojnT%<ryE`{Z!I716VB+bZ#xTu`XsFH`A&|6dSkPk+O}>'
        '~l15M1(b)d;XbH7u@$hNGYk4PKe6wMm7*tR!j&7(Uy#ju&~mSVE+K71m)1e-'
        'RUa?PX1*1A&_3jjHVD)J`HlO&P1{rbA2pj%pI#<*lWOJDTZ`QmwxjTg?C>O2^O3b%HyEZztmE~H6I6~Hrpx>zm`-'
        'lXaMC9wxCQFpz5Su-'
        'o6^LHB@+fFCarn}y=@jCyZgEfI+{mJsnUz{yQ#~H5<Mtw)t4*@$XCZ0>Dj5Is?dACj@1%lc4XpI_t;f-ahFKWBo-'
        'L;cl;=YS4_tphh4<5Ric8ra0YRn@6D>~sHPeCZExXHwwGydP-'
        '5$X%ivD<b}c3%v$d!X}12>1$3j@F1rv$FK)Z%aG61bk;`E!$k*LKEf0h(d{QLkYfm<Q<Y=syR|@!$Oh9UTp3-'
        'iY}P9kL^Ua9<Iq3FEaW4MU&sG7ID1HKf~Dgn(4c2HQsmpdMo=C`@*-'
        'M22ZoL=;vS^n6KP<TGA1^o_87fHk8x#S6n{XQ_K#K<@ceLnmA-'
        '7L702e*@iR}6T#@chQp}tsO@X(u}d2NtY|2{8Z%1{U@-%|hvi{UIZMS0REL6aBs346@zpq(*Bsm-tjQJ<-'
        '2rNf_Q0vHBfOfCGs9P@ptgC01^Uen{hG4-euj`i-'
        'H7P5Qbr_B{OdnbUJcf3fE+%d2$*3A=g93MScr|Z4dmM>)=<MUw-ho-yMcf*VLA`{#<sCSq(AH_)P2FNSwJTE?&U='
        'It8+bMy@0z^sMhZy>>;1CL31j$@`mWtSgo(gF2yRWe$MPzPB>2)lGdE&ls8yk9#Wcx`$`Xm@Us+q>}_cHDhQgCS4'
        '9zS=#Cs2y1%%0FwPUJNXhm@*3}12<Pp&<isF59VJ*J+FMmq`I#J7m#o}cN_M)9pZu}Pl{{xXn!m0'
    ),
    '_portable_underwriter_79773e2a0116.reporting.inputs': (
        'c-'
        'oy>>u=+@5&y2gf~QYX>lmA$cWvEhap`VyU34EoHrpN$1cD;b4)64;DB0^x)4#nlLsAm;uyc1fU~O_ZGaUZr>A0@@'
        'uP7BsRC5;P34_m@oYjw<!BWIzQ<kaV39Abhv8+gVdJ-2|8C60SIjeYCRQ1wvKJCmGR+P0Ua=Bo6QDwmH8=Mw-'
        '+0;M~7gZujPSMnANj7QC>V3)O(zyk(n#-'
        '=JeqE=<j>S=$N>E5h6yKzrJ@9o=amKeI;d#tiQL#iso4k;<h$Wp|I<D(F&blfx7KZDlZYmyzOk~76%JZU*NJ~u<7'
        'ir34T3JR9u_62rm8Hlx3-+1+r$JeY8Z8s2k(68-'
        '%63Unlu`YdiU+fM4PVs;Tof3Z^^1JJVDClEt0;9Gy_h#yxo44Nd1;nPuox`B|7GGh*H!V5^6VCD#sYKv&RthZ$-'
        'TQ^uH;)@iJCq?G*uqPU>*0~c~hiKmVc_?%^T1@V6v{*f7|=rfytx#9#-'
        ';l2{NlH+QXMJS$+m~T*7(t_Fr;QkI%!64xDyAT>Kn<xOn$5yu7-)d~+NAbo1_Qc>U?!$J@`q>-'
        '*C)qWJvf=IY|jWq9%PyU*S3=?||QC%nG-^!N9dAHuhnR~KL2-'
        '@^94FK<@nrS3qT1=E)Z*ptKHzn*1Q>~#5Rp;lWHt=L(+*x3q6zh5}dj^oh7vM+hUt6hcWz9EcWR#j1XH%(rPjMEo'
        '?rMS56O(Z1Xe)q_8@SD17WDU5iANK~|F@X@U%*qO29rI*Kkad1+q2vK#zVSS`ts3snDe*~pTPygjkYx&HCtu!dD!'
        'w70v-q(PF}ygq4l8owW=bX=two*k6+LIb-0Mojh*NTSpxp|-'
        'bBV50;0w`XSImZD&w7gIj`KwDuq<}GTB&CNJbXm?0sW)MiZc9l1u+8g1Q5Wrq-cO~n2L2BJ_xv<*?vXaaZ_#iU_<'
        'RB0<It)8oabcaHa{eV#_n0PqM9e3f9^JC_rb}86Adi;A|8q1{8nMinaa`J`_a_x<q9NwoXM15q89Hl3aq-TE+f+_'
        'E)90$VJv<Va(Gsln_)qR_Xy0zJ^d&g7HHjt;5ihJYD<j<TY7Z0i=Ct^jz3p(w8Ngtn~brM64NtQ(>ZAB?}?08AT5'
        'Te^;@~0N@DbyvR>@R)SYq+(=d*I>cY(Y{s9D$h0^a(XE#+m~rg|=7tWGol1mAV*|)RMY`olXyNs+`a#eSE97m8=X'
        'U{ym}3`ck7_@ZtO1JaLP*T23HV!tna#5_3QqlFRz<bixMpj0c3dlS(o*WDD9fT*mCjzIQuhR;6TUqdiJfch&R?Qj'
        '%fk*U?eims<2v2LXC%nkDaktP>4&i|k1~$H^DJ>L#UOWKFAjsyaKDQ}qm#oZG$gR1&~S4UhK2;=Fw~>)ZA)&^h5+'
        '>qhmxnRC@L(-'
        '48BFD0}MtK@_)1wz(!k!@f6<U)H<P~gphEB8o}X_tOW)pA3blp13@mOEv41Dk!q_v34pcxggQO94<6+djyHgTV$C'
        '44q&$M1C(ZKN^+(#`oe+;>0~1!1Qm@&8D&<9rj@WlP*N}fu$paz|DL(P=Bh4qOrx$5G<~^<U1pmIuU9vOr^+-'
        '<ahY#B;2k7dKD2Q3KHr)E8gt;MYj{;HtimcdMJI8{;pYy4a^+xt}k6gMn?KfT(sL%|WK?~Pn-syy8!a)-'
        'wfiv%{xIO8sYNK^kl5@_E2IyHGIv7!TkW)#z<>tP20y&5Py6dPCI*Nw5W0T03CdM4~Vl=qp<41xPW+~$NBjnDKSM'
        '|QF>87ibuDGMBx>E>y4-'
        'W0F>f!lU1ROMKDp$hwa8>8$6UxsZBZ3y3I)Py#w=*qt;C3ac+?|9?*Kv2Fa^T(>93=I<u{8g;w?a2GOK3ZxFOsjD'
        'v~7ZV0|O<R<FKR1HxgFKEdRLu@Sd#&)WdC8q^1-'
        'hw(~31#Z#)}SZhEr51s8>Q1PmQ_^kQ^>emr;gO;>UsccXcI~hWOrAmET!dMXQxY#__A#ICIUQ~wSm_5uGCsEdTha'
        ';D+FTB9H4*GTc$m3smV){^;@{~BspczkVqi!N%wUWF)YU%8>#(PcJ1JX$orK{dNKsS-'
        '_&}!T=uv15<tfZ_lVzA~Bj&$I3-IOU;XP3+6{jjTQuoa4-'
        'i<KiD11kB_cOYD>*OFUm>An_Ti5jt(<}6`Rg<G(q$q*A}Qgs{U?-jGBGiocRBX~iF{Jj&Y-'
        'WGgyTxS7!FGvB2DiCzjMQSXSigGHJ{gdwpMVBJR5RgHS0?)N#PsH=Ps-OH#u}Ko{=-'
        'a(<Bv=OBBT2d&MH37P0R;iyTnA|3iXx+43S(Bva}O4MT)@x7y?4LkwIaOC32@}O1k6P#K{|`-'
        '_>ml+__?iov=V44<Qf}kPNJ7lntCr685emSfu)Na8WP1u*+yzHI{E=?jhJ>=8Y;&OX=Eyo;N}kt%gv_nGw*9Q^}Q'
        'mOQ3ehb8o!(3*g0Q2_5*(Uyzz{|piz0pV#@K5)*34IY4tF9H9PpyUU4A!jVm8AryY~2(oudv<BJ0??Go9bsG&n<P'
        'TO+TkF5<BB0#VzrkLe{%{;y1Q){ZfkcVm$TbQ)jP|dja2&|~Kp5a(cu64pccqc8;hHqP+;KZ)GrVa+V<u&M-'
        '@baE5v-8>CsS4iDsFO6NeAZ%hEDGBrSPl<WU?*y^AM{$Sha85AwUN-(`LY!i!ArHV&}DyQIBH-'
        '10*#X=fsiNOkhkyqGl1;*=)(9YArk5O4(uG7iM3>h9ubU?sIjgoIrm_-alX<%q9P02OnuOHSJC0nIV+6d?-Bj)y-'
        '*7Y0YI$zL6gzm+TM8$JBKcBvA2eiZMU%#^`mWzvXFwdC^C<f+LJzqq$-'
        '<CiqqU$5drINq7#5F>s7$i^KeRkYC%`qYVa~^XGIJKRv)@c=)gHM++?q5AgHEs`nq>U*?V>#9J9BX6e<(Q@f5DTI'
        'mRP<hG>A-s%E7q{4}Zs@wc33$IS4mXh*)i&^Z-DU602Sl0+u^*;>s{P&v<>_2-'
        '7(RBs)fKO15C7ZMecj|{;nOsCYn`Ka=f8-`F;grVE{7kq-'
        '#+<iWx!g^W<L=BjgS7285(EZp1p`a>Kur3uTcFktyOCq0skz<OqQJGDuG%2%3c_4_W*Ih8{vNJbOAnxeq(R|#VMu'
        'Z(l$I!Max;aGOAu|MUx2E8)n+n*0uEO*FXV?NVo6PHS#h_dox8c;|Y|Rh4Xo)JyH{9z=Wm9KkRh!p8{K@aELtHS%'
        'SnWbDHx0xOdy5$*k9QiA-Num3RNFD2v7s<$vq3HNf`RCWVmQ`QjG<eu#aci})xYRMG%QqIXjcqSBuuh|#$n<{BU1'
        'Z{Lp4mtHCXRWTOjOFmuq)nqsLV^DIR_SN3<NQWiW2d+O63J?dZUeF7ex&wK4izT?Po(w}6sg$UO3ThkObgzfakIa'
        'jF4oQWAubHcsFSL2F!B`+?)qaAJX<p_gjk2ozmM7z?2z>}w0|2bc=30A>338~!!sWzFy>cv2PrN(9ypW$)o#w93Z'
        '*kCA+g9#SweqrX`JZv7&^uc;3;lBqPtzfe0bb1t_VE-'
        '9BmGvW`Vg6eEjve`ZXZZj+Rnf?ku<Z<0|6tcGb8{5E}J&o?s^Ej(PpX@6;^$CoDigIZYcc8<%i(?a?@ULD{6{Q;0'
        'b-'
        '&W7d>{0xuEj)ll);nAq3VfxNzJr*{TgU0{g`6txnr*?(Lnt(CEqkGffX~m{mJ=S&<iVlVD~dm>CZBe!RSpo+PQ&T'
        'p#SYCRT&(ZT6$PzTSfI?b7%?Q`9JqUsfh'
    ),
    '_portable_underwriter_79773e2a0116.reporting.evidence_types': (
        'c-pmCTW{M&7Jk>S81QAKg`#E)Y#&%;v5L$rgvypH+wEeDfEkfPX|_WSJ2SMSr1|fA=0*-BT5^hQ5ZET?%(-'
        '8_!zhY2B;z8N2v<4ENye}sIbyV=N+P*8Pul|$q~<~)oa0&%VX4U@%}JFJ^oSYFv7)@1jYe}%B8X~4g|2x{SmH>(M'
        ';pUv!7D{RDwJU%D3M6*2?8d&3Zywvw5l5=XQKsYjAWX*5n6Fk0_7(o4)lB^K-'
        'sD?s}Hj%ibkVC@DinI(SQylO%W}v{#C`5xhfq^*0Pr~yv;n}HLhz~?JN!0hQTpXf~M}geKkb|B`mju>Yy)qniT~<'
        'U^Yd!f-4S!Mk9ApHD!H3SfZ--uWB$3Ucmo4AC0`f?nsF%MKkoqbNgk4;9pdM5sxIzINYvCrJ|{QUt^&tW@%1pQW+'
        'Nh1ZP=OHViA0r;KMnLy7_{_vaAnI;E8sV%*Vk1nmmWC{OWjC&&&Mz|s5BXteBzZy8rVPzcYlp0W`I?v%*j_Kpjx#'
        'qSALC9eI^BNhj69+(7r(ToO0fx8IYNrT(RNA9<O4KfuMsVq5Hd#7&l5nisily~$Kd5a~Lfwqz0PawL{LQ(WY=x(o'
        '4*_4sKdDqmnAX0*%caS|z@1pa#zJ?h)rr!`OAx{JPl2){AN?=}V*B)QEh2LPhP4D1Z)(D6<hq8nKnoHO7f2Vg3n|'
        'Jd?k}i_f>JG@i{d@Y|>(}mZd2^p^=8OB~`X=41f9{=ck{=(Io8+oTv{<hmu5UEm=YI5J^f~&dEj;KSQ0@(hzMKiE'
        're~xuz7*P(r`LwU-HKu4k+9P{LwR6DohA3Vp-'
        'KA`{WLiv{tLKlz*XsbbCqm{{53xD*W|3f#?Sd{a@JqtL4_x0{WZQs-uY|nD5jHV9QLey<FLiU=BK3RwjY)^S319-'
        'TYe&yBx-E<ejcv=XDWZ7>W?-'
        '1GMZ=wR>@Dv>d#Q%jI^ue{9iZgyZhxLs3$AM`^i4o_N%*iUbOuY#x31aM%BT;+G7cAxzJ-TY|FCoYPOxk^MHwlYY'
        'AOqYW2EHuID$P&yd~b=edb;eyY4=vYeYPXC{n3a*hoHc)MEPKO4nBUT^MPm^~Nf&xILuW)2O`qQJ1l{C56!xmw;Y'
        'lfF5hBMS?#aW#rcOe^PAsh<N+nrEVC8#rIe=!=c{@;^!Xc7Aul_qjP|uib9eZ&%56db|EP*_c5P6@vWMK*$eJ?th'
        '!ThFcP{Sm+Fm(YLeLy3+sI!lAL1_2ynQWHK_Z`j9WSNg74-A-'
        'HECp3edc@GKC86lWBu74KlD2cs78X|{#HC5Zt+&8|S9clyb^2j?`H#Q?WvfU<<Z2lKkt)n=U-'
        'd&KvPRAL$szBiQCQ6~%vNF%_Pa9cGsBlhlWHnW#>DPcij{-;ev6}Uauq(?lCsDJ>1Yfd~;$OvPp1klnQ)q-'
        'ysDN_KP@U{gBU97?|!QWdz;vipYxS{Xo;6$BUY0aOAh*7~fww!rUK%#_NqTkUCbOcBS{p(`1J#>8sPVa(^Du_jnB'
        '$N#nNS6eJ+DFibS0ZS0D5tV!AQm%T?IbWmrCuT6J>FGd0?mSmGrT1bSa7^~H1o$ig4W<H_-Rao-'
        '&@X^Gv%TU3tVH{g&!*Xh$%>6BrwM1taN*c*<PF}nOQNcMTaSRqH2#YTre;YvRCf;leqw|aw0lQvQ}mg&_CP-'
        'Y?!TB>z+$Czq7f#Y$f_Y26nrAf7Pjlly;3ZQ(ILMwdc7hW62u<1Qj8<EnK56)EpGM>g+ZQ25Q!F>OyPTz08&XPhS'
        '&-HEnCfz4g5g2lj#7gQXHd?zwiO4`joXwTo8Wuyr@|mgmN9XNfesL5xn;g<dR9mIL34TG-'
        '#C3HO1Ec3(q+Bql#jg13eWcH#Sr-'
        'p!dF_mFJb>I_=5pxZ{va4E}c{eYqBU~p(M6Hzn5Do_jsh$LvgmVXd4x4y>cc%e1NHkAirAI93YE2Bi8@~AI$3@xO'
        'J+sZ$t(%q+R*<rh~y<5YziS7DWR1oRY_TG`mE>iJO+I?m73|8ua@>5UzmGf~gX08Zzh)gT`NaQyzJA?A8VMp&(US'
        ')=*_c071$g{q!@Z<eU0;yT2zry|>qk)eCUl;40pn0lIczz^nNTWZxjB`?8DAUwJtiu~U%_m=#G0sgF>AWO^;Ljz5'
        'AxMK+b&>V|D;+NmX8--'
        ';B(qlZSHkF?L*ow9%A&Etd~wiIxy!fGXSd6)!ZZ<$V@x9I2?V2_LoEdJE#!QHf;7BIxB8<@j7~q)90R4D;7uL087'
        '(S3f&#~RRp64cL-'
        '(wnKzG_lKpr2Mhyx4(aA^wr<nTo?yV$M6FQdIiZ2%9nY5%d)_`l7lY1h6rX3{}w0}=w|c2or;>c}bGAdjC100TK2'
        'B9WsyJ)J=>sn-z795Ec|i7(;UfuZ;`_5b9l&;+Q_Q4K=Mezpu`h5ML3_Fs@E-'
        '867`(>PAAy0QP1ZL{YUWN$_RwRHPZBQ<Q%6Qa!$hkr7=n{{~tZuRWO?ItS;E4sb*uic+UVA_t8?!c!T-'
        '~Jakb?=?LxW5|O^9g$OkD<~q7z$HKAY=-X6xJV@S0qn_;Nrzw$wn_oGF(jTa-'
        'o%<BK?`e?IwAP=yh}Z@WFW_wYGYne)wQFQdm2%BAx$^JYttn%P$^`@aWWCqyGWl<z5c'
    ),
    '_portable_underwriter_79773e2a0116.reporting.evidence_values': (
        'c-qAoYj4{)^1FWpSNBB%RH5wwSDcY7u-8p-LEE%Qg53{6AkZ@H=&IL>lwDu0|NUn85-'
        'H2FvcTbrqP0lQ`@xxE5Cp%`B41O%2+wFiTe71?$9POy*3_-'
        'Yt1ZduO0e&O&}vOGIJvFc1IgE{61m73CwWE6dd&*LcDS0cWU;t^Vw{oeiDln7p)Fv4f`8X!bs#0pt5+LFMF-'
        '1>GY9l7%|u>Tq^jEz82UHGuY>@a!y>DjgJz4=Eim>kmI;8`A?NUa(+N)Yxp=BO0n8Q!Y$M<DY_(=BekgHx5(L3wv'
        '1#j)r0J$Z9@3QLC2j&URV^fCzF6qBl8PsF-'
        'e88^gsw6J^qDpd5Qxbg`=dkY)#<7$SFGjc)HTSsZD|pcTSg0u9ZrF4l#{A4OAV+57T|BQHk{%HT@@_tP@H|6gTm5'
        'xe}DJxuk0;-'
        '{pQWz5^Jr*7$FshhFSXIg212j`sV)X_Lukf*I#bZub;l$rys9xe!Yv;=GWUV|M+zEIsN+O_p4j8cz5;rmz(?R_xk'
        '%vWB&m5@>lLyNx>sBwR+v#^lMRzk9oCL8@H0t_sXT>MYLEf)@(yk?PRHOu(Y5nR`5_e%93!=#>N$wKAMQU`Wdv9+'
        '<~bXUrIU(d`XI&iwA&xB$wpjQEv6FyCmy8liM*7T~n}!dWFsvlO#zV5#;%Y1lgc3(S0ht5FK7Kl5AR9vIouNV<Kv'
        '#7e<N)%LgDzn*#hkMW7Jqg%(>BlTBbk%!I|W{_#`$!-'
        'iZCS)^Km1L8$QR%vF#L2rSYHm}>%0qymWY?%lprw)zH5F!URtp&NMD;2kc?Vl{hLoYu5X=x6*;5X#vs%`5w^me6s'
        'rxbuj;^5j4^IA?!I!|<mTo78W@@-'
        'dloCHT`1BntsqlIKtsmS(E9jO#hKS)J9_6j=q#)Rl^8ptcI!deE*R=p3ZJ;<Wq_w4(n=Pij`i^&=T^fFK$7uY};x'
        '2Lq_lBmPd-'
        ';e!OX<f9A`pcYi%zl^1TFxsPI!?j9XRLwLa1VS)!^Dn}q9q}JA)69njepCV5sV*b!P!E)N)C%$P{;$JJ`s~}Ro9U'
        '4swTl7X%tDX(c3+bT6bZfcY-(?!7BNV31W&yU~xT&i6h-'
        '8xJkofDDWEEvNk}Y39Y9IRG7!d(6q1)I5tI1XJCO;Fop!Z#TUnHq0?xzNt*uA(V_yMN>h1Zx0axGCUc##bOXs4vM'
        'K(%v{%)Go6a8{xAM}w<6IWsT4z=dL7!qVUm`6`m5QdDS1^k>s@O;(E~aQKfmk;U1BsH99TzeYLt^#7b+O<iOqI7U'
        'B`=BmaQQiB78iq?$MxZ$$Lf$|1z^_q#UODG<kx6)xcHSqG)EPRw$jH6NSIO%@+NSrYo{S=eilCA-'
        '`<(itjnkzJ&WZNB%V!PLCq2#2Zc<+XReDe85KfDrrtA6dUib`bj>Ew$pmd|CqIJ71e_OfG9bbp{YY%>X<I?!;-'
        'UHBL>QJHPGHGWqmQTKU@$0jLE<Kdq3O+0$M6z{)Npm9xJ2H6UNCq<xk}N<KqCfi5XmsspBTwz$Eskbdk0g!g%kA|'
        'djBb*HCQ|Vn~>eq3r2JgFo>q<sCziZJMmX4=m-3oK}>-'
        ';+SaAI#bI<@?>S_Of>l02%auBCNnQ_Wx=uer6r};etZam-2Elvb3c$Pstpt=FS-OLI0N@R{Isj(%7c}^u<=ZDQ0j'
        '>@>;A%mG*P9Jz2rg3_NM=sy4M==)2TCD!l7u?zkWdSnL<XHDY7?pm%4yrug9Xg$vY~Cx>k9g!99joFYL$%YSF%P}'
        'no6C6JL9sF!CMY{j=fZk$JLfS9?h^CQ8Mb#gd~_f`7Hw?-'
        'ioK*Q#DiM0^A~b9VN6ngmWlqgIKR@Y7SNGj`f(OT9Rs=mngv-qXeZbR|hCKs2QrTZY7ITbtaL&WgVwWq*;88TF0^'
        'p`h5i)v5G@Y4i2m_D`wBeFBJ6HxM3?En+7~GB8(iG!>@DP3Gu3~Udea^BT6!wH_VK3=#f?`l~`!EJ9Ka+a9x$$HL'
        '06@T~yYG9Gq33T^#owMpO^rL{q;QMAqErZro!QUf{~7lCJ9L?9Dc`m)W0{6!qCrOG)&OolH;Zw(Uo>%pt$R)2ohA'
        '^onl`11u#U3<n?(imt5AseF0{0BOlIUV0YgPzb!72dU~v<;w8hg=BVKu5Dv8EHKuf>Kwb(^D#Tf2eLO7(g|iA9yW'
        'fb?&u+8?;({*GHz--0dz6*az07zI1QgrO9_Q+*_CO=iX!DuO^)itvN8dN8d?nM>62<Yf}f?QW2m``I!$lv!ZMkwU'
        'KOmAgG>`z&%vfurS$>&<AAdrBtRj5ub{AnTZW6^$Gm*+V9&XkCu=sEdJne|Bm>oGq-vaNt+r;n91WAob56GPH_pf'
        'e@(hNqYOW?}L%<F;AI6Y8&XLvUN=YkSSLA?5&d!O8^bFrnx;omnz22MTHM!8-'
        'Uy!%Sq+?ika)L?YA1fyIj8#y$Af30tar4n%p3Xgbeqh`;Bz<!yK?iq$cQ^MRy^i`dG};iES11f`h>05IBRiOzp{u'
        '@C_1?U)DCwSiq;Ns>TH$&O?@tV4Vs#>A9}ewpW2U-'
        'n&1FCQpRnX6ct+emj$=sonrhsl*=vegq~CIA&yOdXBX0&L_!@u4m~uDgjVZA_%w^dh_?*%y{C}#y9Ut}$a<f&W@q'
        'DM1HPa{ge*$>&CiHF=bpU)VxCl^1{rAuP_Z%zQv@8b*PEm!WiFsuE=l$nTM9?jtP#c6MO=W#Dtv0s_Kcl~y{rZtC'
        'r#p3r?*yM2!!={g<$a4&S1pI?IVVMc&Ir)sxur(SyF&O)t3R1mC;F!BC6*bqPQEA_v6Q8sRQYYfi)8Vh6HW?dUNh'
        'u?Z_euizHc)8^#U_$F>o%0HLwK#-zijkp=^lt_)-yp-'
        'n=L#dvl+Hsg>)hIOw_M=uB?XbgGFkrnB!%=d6d1csLNv6ZskpqNMUIX6-'
        'y9m_BTH(2#b|{uyieA)#VT)Tw;>4js3_%epz};QK#Xz^Gn5N6*vy;PJVy0q{x0y+Lpapn%nM6~AqMw$I0p<By6xT'
        'Jx}|z@{G*{R(z6_@y0|XI|foznp&(dzp*aHyY=W!1V+FDPi0nr^4KOG8ntD>PE-'
        '}@M4XT|2V~@#%v~{_65ipgpT0XKC$>O7#Ysg'
    ),
    '_portable_underwriter_79773e2a0116.reporting.interaction_evidence': (
        'c-qw*Yj4}g@w<M-h93&Dr?ANtxNFraK#=$f<8sN>PSOJmfmn+xn-'
        '_{?NGi6@^?&c|?(CCGN_Gw{8XPQXAM@Io*_qkhi=yal-EL`F{KiO8^{l1qzNjm*uIn~0D%!JdPFmK~ZC_MZq}w(8'
        'E1^|RnzHW6mi08JJxyn`S9R6xwv3z_FehJ%oK<Tk#-'
        '9l&Fsf&_{oep+ziR=}HCumTxs80r)U=zTzb5@PgTbG7tm|Q%qJV$4tm|NWO5VeeZJo37shL{0pEhNEGh5TL>;Op7'
        'kxktaM%UL4ryNjO0OZR(kV$}>20GIyie|G-'
        'TW?90ZFWE^%Q8}Ik^8FdDWBcpm~~y2Ou*|>dbw5uf1*tTVv}RInARojI@YOv5Nt`;O!oKt#`NIKpWFI&{~kJKGwi'
        '5#+Xe{jNY$vO2BZrO@L!WFnt2DkELpaza@O9o1@M%8|JU!o|1<lRK70QByHqb~s$`Zq6vQ(E|FTyf&OV-Gr*Ge%o'
        'V|SY{`B43?8no$ug~YQ*KU9H?#+jv-e&L4UZ0#{_nVWCCvURXr!W8U_TBmW(^oj=-02>H{nN`|oUXHX|FU|{Kb-'
        'yW^3_T9>g3HEY(6{r=ZDj?lh*;FaD-CFbGD^bU#w+oKwk$PKZCCSSX4P;vNd@=OTI?tUud}-2%WYq-J_7!5>2)ST'
        'fC~<eOA&-R(9CSl`7k`bc-}+l``jS1EhC@)*ISZK!EN5i*1WFU@3Ro3L8Nwiz<`MVME<#pEUnj=Lj&9^w|)As{%-'
        '4ih93U7;9DuvL7S9qH1=%F&0Z9UjA}=p8fm|bl`k8o8@dn4DXiNXKDeY#0@<Q()Fz*R}EQ=s|d2U7^nn!`XV%IA!'
        'dPZ`G}Grb>%u<?kR!&;tL}U{H5#t(~fS~&<6_-6%=-'
        'ipUJ4uV@v+T8C`IB^`z*Es_QA2kCMVX#7`m_;{RG&bc}Fcb<(zV8%Np|Z+Bf!E`u9Gq_L{esdDh(uQ?@eK|nr|kK'
        'ASuizPcfRUzba;S=0G(^??hc65l@6cmT<%04UE7jA5%-'
        '!<hVw>BN_WK9m0Py#%=6OLtf1P$9Z{eFyX0h+HnS=x4P7?(QX;NeY3bVFNKf#Jbq+nBJ~K*0u2xs==B)75t~M>`c'
        '4yJ}VxC|4vIz#kT7)#PixP4BwiHXxD9qAdD-'
        'Y`hyWG=w<_gA?8;>%hfymbrM8u+0V{1WxscLlXUl5&7E!W2ln=ui7Hd=q(S>U`7X=j05LmW35&ihXFC{Lzq^NBuM'
        '}EHU&wP(8Vk-'
        '=v7sBKx*gGH0TZxH5fC2QmPf2{ZbgbXz~n78r}u>>?BRo6%38F6<Qj#BoS`21%!>+HKYBOHqpYDfrT<tfoNvWY-r'
        'JfE~q68>Jlp*<V7_a5RKxW6W>qqy+S#JG2&#mk$h-zEn{~ZoekZrJIZpn{6RN9rYVEAw5-'
        '<`&a~jvi%2v@tCail*b+kGOkP0<(Xk#(BWJg9-'
        'qy|XeY<0*N0^adP(IX5!!!4Y%Ss1bmavusp(&$Xx<Qkp&Pz|R&5A7jh3V>DyJpLv@0NYO{}hc;VnArCU;0@_th=n'
        '?=m?erhk#1BRLW@0u$6M@>F8{98J82LFQVC{AKn_?#ZQZB73VGkv9Fn>S`zJ0M93K2+{6eGt}jS^`Kw-'
        ')$r#XbJn(0=7>PRsSQTXuNK;Ez$;N~{S(0y$4GGl#EMfsp7$^y0x6oVeNq<w54Y)MOWxK(CE>Op|TFE|7n`C2@h+'
        'JC!;GRp8DnPm&h+ttm3G5XjsFe6pMVad*2JCKZauldL`T3;1SN;Z){`!XHCe}hiE}pHpn^(V{ua1-~aU=^-'
        'R$hRDR_h)ypzpv@N{x;PKHQ*YF`jfP_pumBW0j<Rl{-R7jdLDshuo~{HtV)^-'
        'Csu{JJC@bC}vavCtsN034nlROv%#$W@kN}DDV_KUiIJ+FZ}bj%)6-'
        'DwE&kzpr|UD#n0&8Q9D$NI4e4x_M*~hT~`})Sc{W`x_PIGyC+lHqbPi6Bp?=mGcwKuS8>D0#Bz*NyMf@PSL_c-Rz'
        '7k_0e;FHdPL`h#$DERxiAiuJ0R@`croJwA+2oV;(RxGN}D1Tl`7cmGY%-'
        'r`A_LCyF}I|y<v(_XXK=n+A;mH)qq20>=|1av8;h`#KT;`amBJRm`%!TAQ*Zbk5ujV#7jCwYsehAKTy`l_pq_t+D'
        'cq70I}6ntTpBm)m48D9xX4{y>w_m2@l@y?)6qfZ-Gs)m^ixSE&vE~j9zr(PBSE6F$isoYR7bA-'
        '|pQJTtFgBtpeO!a9k@BaI)JqYkE^7IDia@72sctm9q{wpFxzoQHx;$J~u9)VB8R9k-HIu_oS%{?zI{w<s3OU5-'
        'X4s3nc{r^5J|a^?-0Y#{PuwD0ga|?uDVMsnEJ2e>6Y$@bks6(mUzSY<7>}R05pelQk>LE}C`+mVvk-Akjs`;Z_<B'
        '^1wH}rak?E`?-'
        'mV61Zm$`raxZVWD5oHb!WLi!Xwe^XYxSLKGC)02)ZGt#2%$P1ZEVBImCSdxXSoaW1?{i>Zz);g5Szj6ir@Y3d~5L'
        'K7|brft!6yehjCny!EVW#YHQkjmP4r<V&S9UIjnL*U62HUzjJ5&4F2drE(;dEyJ(EX!jYl_VJCvvynby<n|`ur(e'
        '%wy~HChg)OEL535JEQQUSRe2moJQ8m?k&q|C7o=)eeX8o43I*p03dN^^X=-rR10{D2R-'
        '^Duiw;LA(P>pe`gl2FF((%ih}eMeD~}SjoPki&ET^tkz+AJBbH<#ag9`$L#Wp>ssx7Xr#TQxGaCbEy_##ltK^nO~'
        'whw4xw|7o90fD7=vim+tf<&SVhd;uszLGlk4C=uIPQ+4|^{&cQ9d4?E3wbBx8y(XnJGaz2mdNQd@_10Kb<#rFdmt'
        '+`z%12UIR5QXVJ56dJS;iM<mn4-_uwf2JD@Ap1<&B-e%5!dXY(B!7a)f$v*1<5Jid_nfF-yjrPUs*tB*=Ql+lXq='
        '$d|EV7kTU9kcHwL?hK(txBfc8Cg`DI-'
        'x~A5<KNn0$_h{idA~0q9UcVJgR<v3~l&1N|#>^;%8&9haZT091C)l(Ni<<v6=AnVAAOFjSJ8t#1_Cu$i2WD0n#yG'
        'fN?$Jf&N|s;F6U1ga9DbV6-KDeZ~4~z7N@9nnoMWM3Ao$SB31Zg5gCfJ8{!P_QwE8sf+-'
        '^?bA)0)lBJ#S7~2o;)+NtQr+dItf{DLH2dWbwCtGXI+jemKu~A}Ja5DN7`g<;BkbeYCAfq^pIA?D*RcGYmLZQ(_&'
        '28y#R7fe+oZ;7SAM{Y9t<pvYGcR%=))U-jMATzL97!D1wt#RLJP$8fQ2-ts-'
        'b$ESOT@8e_xVk>9b=To?nKu%R@@SiUpORG<8?-Y0;20vDq}V?F(9FIcp#=6vzJ{C|(-'
        'c)MZg;^y;c*SFoO#8)~YLBN{doh420-'
        'daJs6T5*Ju=E+RP9H5%wfs@N%UBuNi@^7I<^WS4bmt|d33aOeDvO#`PXf+QZ9X)H9F279OYw+p_A}8HS5QpkPPJl'
        'R4f0_0x207$Gbp<<^Fn?i+3X5|VIavlf=5~dieh?dmd3X17a|DgG4|Af%<zcEHQ`UE&ZliYaTVW-'
        '86#`403@XU+C9{^^z+h0PbJ(6B6qQ%eVz0>M2j#juz2p7&D#sINrOKZ2z`h6Q4#RQ}n5)=8O#UCMWdSb0b3Z$zn<'
        'M0L)mE2&0-'
        '|bC8H(EIgeH0<JQBMS&S<==6jRp*4Nj@GqWFe2RWXoP0uxyZ#D;xjsu6Pdf4efMD(qva&t9iJ$C&j<fkK0oWCnAG'
        '*si(SDT1I>cXB7Ciz+D5C$i9DWIQ%{KNzhSAbFVA%8QP|mX7zhgOxWsOO|_*wE-'
        'i<3|(=oPb5@AKiIPU8DF(E56X);M{lgw7U5k}lnhzdk@Wp6t0Z~M0gF|Yys*kHY7l(A&f9EDyDnPU+YSye1+^z$f'
        '%5oEhLZH~4m2lwefw-Kwj)hW;&HAh!Z=qEGAxS?3r=e6!oQO;QAP4b_`8gv#w&Dj6H_y_kXOe>pg|0d0EbbhNQ^;'
        'deO<y-eqDA+{*pce2ME4<Q&gKe7NLKVvZm8C8Y0c|1C>u5ND1g`aNrB_958(2;!PgOpMt9yykz|iV-'
        '<NO^x?Uy2o4>~P;0s_izWtn&pDNeXKRzrmwPg+kcPMLaHcSUVXt@J>ad#&8Hd?dwzOY|T%8!=-'
        'W9>g%83mq6HX#fase~GkjVh%gyLg`@je3Qw*DK)QJ$uAe-8<zDE=ofK{oE4Mu-'
        '_9bd)w2@T?;@H}O<w)UzIy+D!Raf#9%*9V8xZ3G>(m4c=e$!haVsYPWmg^}xB)0E_WHSfEr#*4CJ>VqtJ@gr^FDl'
        'NkH<rFR@N`kv<j$1_fxd4TXo9NT!;QV&&bMmcipHWpE<z<T=^R_!uQXm<<UT=kD>LSqi8QEIO$_nDy^vJb0#PcKj'
        '?2avZsM-GmpGvuYEe8U%U4ZAwtgd06X3fh1##_>R4km&`c`O(2pvN}!(Bz4?u9mYJWWiiWH3}^V`;)@}THqfbX!^'
        'tC@CGZG$&V6E+1ACfcK*Ss4gGAVo9D6==fLROlfyl$xL0;<TaTV-'
        'r;!(_;SE<zLSB96Fg>u$qNt=$}B7LZ8V%2Tpwpu_7y(Bz*DdadcH6j6wj8;){gyjTU{VFsEhec@P&Qv^ODGr7Y6K'
        '^99l|&zZn^n$mKspFaVKkJ_yXWt##~psS>AZbvXjc?Cs!SgPj6L)WUh9-{=OjJ=z;hn}1l*s*-'
        'l(~YEt*pHS^P}M9~@M?UHk@9*6LyOYa?#2Zy+uegUqpqzC7W}c$M;}o?_X$SUk;;Cmix_)sn|}68y@0?&DPGu{l1'
        '3Y%baMpQiCQmP-X2JQu&D-4-1HhJCFUS(CY=x-'
        'F_=yW3`bH8XwN4eh{BDFi7Tz9p@(hbV)`6?*dYjAYW{><2&p6O)_!53uGUi{a4G8ugPUQ+kGPSiAHN?;%-{-'
        'YAj>FwR?s-^CsrP|^+nv#su^=FrL&TvES6LFu}kWJgOOzC#W${O$}q<5BOEW0c(a-'
        '!laDS<iPA>5=N~DxaysC@r)e0J;y*c-'
        'Ekis^uHKS><2S7(C`0eZM6=bM;9S$`r>uH^4QFqZ@`7s%W=n70B*NIT`T)D}tEuit!n`Ug12hRS#q&5<}uOqj~&Y'
        'qVwp$wV&f&>xEt(snz!NDrCJv2^Qjh--UfNc-VM{7bw?tE|eGG&`urzDb?^4Clf;@(^A4C^JJ$oTv^c)v--LR4<)'
        '-{s_2OkRNC#fN~A`iEkOjcE3I$hhAIziE<mU;7Z3sz#>;<m+ZBRaxibUifl$nWis1Z$&xRm@8_8j?sDlES!>9yvE'
        'Ol~H)?I^_62OKC{^ZEjDGbT6v;P2HP9*>'
    ),
    '_portable_underwriter_79773e2a0116.reporting.evidence': (
        'c-'
        'pNzYj5PZk>C4QX!S{r>rrO*fGpCtTEOe=35?9^?Ac9lMnjOh*|xH3Nvp?<9moIuitj3tQhSUnf=ru57ORTIdXZEd'
        '$LCE|vE2|In?0){_NCmjddH%o-'
        'bZ!Q9gC{`7mLavx?zW=V^PQ2rW>MNQSHX67|N#Z)5YRyD4_9cIow4%i7yxUa*b~teF04SVqnp5XR$Q(!0v~Y9uyV'
        '(q8(Vb=vY5iL%%{Kuwr+oh~%^#S$E4|+_42BZYpLdPoqn=Yr1{3XNR&b1%-'
        '>M`~pnWrc*vVw5<OhXoA^_9q*(G<Ue`$p7%#^!%Di?+?V}O*0)hR-c;o-'
        ';>e=%$XV)vwPOJzi!Vi46`Zg;*0D5><Hh38HODB=592U)EYH;tV5e>dDayq{wH=G$PWD%#5rQsmc6v~<h~U5XMcV'
        '=)EAht_`(xw;t`<u<6u2pNRnhmH89WTcUlpjMkVX*mr>?nw_zYm)R})u{$MzvA`lxPoQwwVX4e-'
        'BquNmb4E`fZk_pJNcl_1Ofhrj&r!+*2yi`Q@7{5h3s0Mn#&VJIp2`PrwlpD*5Be7@LRNmlcBo8LC?@{13jH<xGUp'
        'D#Xs$p3cn;TH}4boue;cboV5r;mT%T<XTFi~rl?Kc8J`9PiKmK@ePi{5yhN{d)QK?0l1-'
        'Z{EFA&6k`1{q^E<^9vbu{_)+f??0#>=S5rGlvO!A{8}3Ykf4oX@GWQ)ZMo#j);o<?phfji?o{hNjC$Afy#_nYSFk'
        '~TF8Z>U?QdDZHS9tNv4HM$*o9T<Nx-M78U9w*dnFLi=*{5(YDfpX=i70n=}c~CB|fp(=W5GKjUC$-'
        'wt5c}zGp+h_0<D>f`3^p_lF0(WJMon26Hrwy;1L%X(HHz(NjfbvGN^QvfHM6$YF_DrR1J-'
        '2J%B!9F;I~W4`hO$hG%czZP8$lN!JXX06=8EY*0doyIR9{zl0%Z(1&oqRNGhW4zOi7IY4qyR367=Da7`luHiq9NI'
        'W*{@iA1%xl5eON3h1?Krp=26ox|vx^V;=Iz_f`RDwvmlwalj)lz?*oJ5SxVSRFmr>wba!QX~l~7+{{}$j=CLEl^p'
        '~SZiDf_<cVAxt)*6V)gR&={;SIRmIgV3*yMZb1z1$10SuYLlQyCH;UE%3zFxpR-nePz=#MThnD!fPwX`>O4l{kUU'
        '$>rT1n3hGFr{#^=ic>n<pQQ4PuFKkXC=UHifmy#&KU{L}c+^cN5uIZ9kk#rn;9%n=axIZx_Y7WZfbJgpkp`nb%uq'
        'GVgZP$z~+pm#8Dsa))R4UsjiyoiE00?Cwq|;Uy;JGC+DJaviPY~6i-H>1;L>^)UUrE5`s*3($dnyLfo(-'
        'U41;joC^YwO_f<#!oPs|Xivd#=4-U0+F@o{M=rQ-rH`e*w2i>vyqTrY;?6<leJTdp-HhzCm!l1Q4~csVb7g)5z11'
        'GBQ3<||dYo~n&ZMQV{{0sN$E-;CYPc9Vb7E{dFtm{lqH|A>-'
        '=MDWeZ5<+rXX*vcmMjbsae95h+=bDf;m0Avdye&W^#utNzf}Au~5ep=_NCCn+FBNFH46a6K6<mX$oquhluIzyr@u'
        'XbAJeyb`+$JrsKCVN-)0F!V#-'
        '8*y7XCM#R*}qY5788)OGQ;h;2|MV>qK+Wb;X0`O=cI+g?0UNt^Bvyz~`y9+&8d4QQTs>=v@`X@`thsr3r2MIOMra'
        'yTxGJ<XE1b<xE7gJspi9c06u%7({^rfJPhh;}F7`1VfU*=COM(rRden3#+(bmT?zrdS@t68q9d=kXMj9Q0i>E6@Y'
        'DX*f+!WfP|>0WlR}K*Erfm$?Q)H#xl>`R5Za*w8b%}{vZrRgDi6y;?vp%9=2z09B*YK{zT|>K%WJId^<|Fpn+(~@'
        'L1GrhoeS?!QGt-'
        'E>cmxlOZ)6VCX|)mu!ixxGD(PWwZUlBw9G8Ci<^Q)zfrJ!#QocrKwal3Pr#)l$$b$Do|0Qoq+Q<-'
        'YVmeLtHo3V)l?ZRwZb$@dDAKrRclvNm(61G}m>B|N8aTgike3sc;mjy1ZF$*Tl)}Oo@Q^N@A=1F&H_l+5B%TLH@T'
        '@(b$Q!fb+cUAth>gS&r=!N$d(uxD-Bs_9AqX&J=x6ie3-'
        'FWDNRts2~vM0lX2(lxVR)9_?=~bPv6C*E`@uy1hxmgN%<9MKC}^c1ZO?uEkx~G-'
        'RqgbEWVQH{)R<PK8p0t(c|>+i;&MZ<_^-'
        'o5F<bzK17d|Evuh#ujXlLL<!{Y<Jm8@whgT*hPZI*ue=*0Xyj$B7zSa#tD?Z?WCGz_PA#fiQb(e$kSaOK6;IOQ*Z'
        'z`1qL-'
        'H(MKZ<9Nom0DuFFUyO<#G7*^I_@~lnsvx4u5Fm}=|(;&nq4btRmS)*<%VU=OGWgnUv7*iQfUa>E%>a%1?V|N)j;c'
        '`Bz_LCjr1o8nVXw4znizI;1!XoQ1726{lC)}Hm(oNG;QaHj@fK+ZFXdi|y37TU}C?A@LQA-'
        'g6+O%9W+LB8IqGAev*$d6#($vHU<7OwmUQbt(qkju*Dm^*X%{XXeV1XtJLJSHb!-WTAf~TjPt2LqNb-ig4kMjGX$'
        'jIYlTi-'
        '==qyo&HwbK+YO*s#eAZ}A0<Aa<^`uf|t9L7D1r4}B`zUMA8vm;(bkn1M`St{$by@~u)_n9EaBZ$je&!W(+qZkY&C'
        'nx=9Q`Sij19<Qtdo9&2Ygu<Jhe7ag9p-'
        '@tC&HbTUs%3B#9Jac$wJlauGg#RTFx!QA^8(FtDU1fpk~7Sb_>7S2WwsTjJ4V4Ze%D579%W`yy}N5-'
        'iZqjtX!&rI%8B^%4CTY=`}hli6BA?HVc>_v_D3#)7Q(is2`H$x2&keYm~We>Q^<pE%-'
        'vjL?Vbp;KR<Y38D*Vgm39lc<4F@L_(ZSa8O7@q=)0EhGr-'
        '#nCVb8#ef8t_Ty2z0yR;8S9C6i(Vr9s;8Ok&hOutbf3dFVlZvTzT!N$FCy<$#h)RzQcg<e%iwYHp4cUXTrbbZ;Wh'
        'G+<lPP+5Z832KlZGpyYnBc6AW{Z7oT|*>EG>&c=QPOps?|BR!-'
        'LJ5x%gfnhLu|va76MSB4JK`P9i!{{qZVA?zxS3BD!5ol<&Nw8h_||!r9T%(=!fINYddQr^IgAW<5_9Jui_V7Mg)u'
        '2t1*GWb!+EaFkpkp>#qoRO+9VLWs;$M-F5zRr}PU@v$LFloN0`K<KoapbR<AL-'
        'C}M3Epb0D!OkU;(^pF_yn(%+%>L8^@FF;D!eOdUi59g@?u7a489`YWg2#3R&SY<;Eu(xy9>xJz_~to=0eoJi3rWn'
        'G?k%lMyM3?Gz`OIw2H)jBNaj{v>?`NA-jBoEEG~HjI!QU-'
        '2Y0PcAmSU&+mcS_&&Ci5U991z<Y=vp<Y0%LX+7MFCbI}l)WqnR1Xov*Zgeto)-'
        'b+?3Qq~MSQm|kzFh4ZG(bNT`>R)RtJFBS_CG!IE=1YJ;b6Ym8eO7%z}YXm{Av%ySe4n2!X$C`Vs|1@~oxl_GK+=N'
        'Mez+u!Uz)i(<Ny5ZI1gX=Q>ReA{*W2PCfWW9w_KlF>`zU^!F=z$Wf>w})9BQ>8?)a@~szwB4t_zz%xLH;_usJdLB'
        'Ww}s`~uH5H6_zn>>$vKy&wj3t!J{U0~XjrZ89dwErdU&CcDj+cqs%=T)hjoxdx$<7#;DEz)x|_+NRb3k@cSV(}`b'
        'J`$h&O?Mp}?%eO*7W}UN3;71Tu!^^M$Vo1+1nV668rm<jAJmi&j+r2taMTZKs9-'
        'AwuN|X%YBenhqZLaZ{xwi8`OO5_%HYP~u`HiH;iBYT`mFm=7?JdZ)@GR52Ig+r~}T;0w8a_%4v<K5A(*y~MOQt;}'
        'LZZ)ee^%#>3Lm9?j$5)=LUjj>ZnRZM2;-w*|I`7@#>f%33-'
        'L`EW_xr%V;qzn(9C;}tp$<XhK5~p1|Kk&zDD{SUEYHt3?_Z1J^19ueNik2y`eQPmGmFogiJTu70Tg&*p06JTB5L2'
        'eTxFD$mpvSl^x}hv8?z|v;jGyLe5EIjDoF%_CA?%bpX(ujg^6)c0f;l>lM{NV+m&~WoP0!b&o1<dZ-PnQtHqyPmX'
        'ikFCn^`TmnB7-'
        '1*E`MmW1)G0cB69063#0fay}?**882>2x{^~<TmK8rvAt!`3R00#_ImhRu@eSx%{PL())nfwbW}ebnHYan23v};u'
        'akY%<`}PnhIGkIE=>xEt3(o!D0BAz~rrr37DT*IGjN`S2^?vq;aLvHU-'
        'r>KNIDs<9&H+TB!aN2!!=h#S?EMtR0C?T*$Uj6$zqtjV$8UZCdo=Hk7{Kl!~V$T?r;7A0bxCMOQiMD=TmBhKX?!7'
        '^oW_i~e^$=2{Y)vOf|*+cF)RTs)yjmLm3-c_8crNxIA%l-'
        '&6EvK|tc7^wPVWQm~bnj_yXQ?Ahx32%@E8JKme?)X63BMTVUvT&*xk)u`ZbZWF(S}c1T+&mIjtRmL6V!-'
        'mp_oUp8)OW{@uzMJ*7<M{p9-'
        'xE%X?r};QeI%Q^Z#4(W4u*lE|&<EBF2>Wihi2AkUo2r<dLI(qDHOY531nr#~Gwgkd^{z{GO}J0SWJ^hj7RjWdWXe'
        'ib8_OK%GJY?;$c$-b1FQP7jszNi^SOcEocniVB-'
        '00&d0Sd_p4pDr(V1Lvza@(C%V#UEECTIxz94=4&cjl<ZDrVge{<)9g<nQVDw)kpwQuQLU3~Ta8CnfSVpr|F;Dsn$'
        '~Vho_>;;l;P&7jWp;05Yv65MW2)ZO;_xGX9KBEIRXTR#4iF<G69(Q6*x2YE;0r$ypkJ=w1^&fh_rpiMObme;@VcO'
        'gJ@K*@QbV{P1EgU)tz3ud`8us+-~@`s(XlbTXsh`LDup`Ly#Xn;@aLtgXGk^3K6;iF;}M-'
        'I4EPM%Jk&&Mu4wVb$T+HQ_2gV!-+W$ke$OcJ0MkO4sMgf495Ys54b#4QE;U~s^S4k-'
        'Px=r;622ni`f@Q<eoJVwpS<Oh9-'
        'RXpG=vyRWszjmtZhJMW)_VLhA7t<B;wSLMza1b!|caM;;8*X>b|GrswOaD^$VP3zN?)!?zIa&6&)(L>cTZbIDBma'
        '{hoJ+OevFrDb3{Rl2HUlmHUvqLugTpsYtWQ%DL6E?mG+rY*rY*?jAaE^<2;zSsV9Qhk$W_5^cklrf{|Zs7}RA^4W'
        'LH`Sc=Mbm0?;f;@%#;tVa&1kRXled+KhLm(AH*YD(#xp#zBp{J0>sFpB0EV%sX1)5<G}y#YbbN-'
        '};m*>5Q1HMuzu^yqb*Trvf_^3$2!|GL*L;NtYODtyxX7FW^1P!Wq192_MDZEn9=<ZRFIg^zP$3hL&PK}~A`xA8K8'
        '@b?r?_pql^VkBmZA|zo=-'
        'hfa%h~EoO2F!D2`?2x?Y4q!YT2xEp`hW9G2_PAqc~l=+R2L#7n6C=xvl_fvuKNzl?4NdlX=lBMYj`3ZXL@pLkJ~O'
        '|b0tbGIIak{czvreiYwpF)nhP`n5bxTG?LP1o7IHjG2ALZ%kO-pj%IoyjG#M|DPXGNi*NAEjU=u?2TOyPVV&Rh<#'
        'ktmS2^6RyF@Mj=NBOA21hXtu2s#D`8k=6HZ)K8Dn{hh;>rH163KFvf!b-'
        'xkMXfq^%mu0V4?aHtZVf<Ikri`aGzc*CRkh{RU!Y)MMGD|&Wls(m8NvP0<1j;3cF{!WY@<-'
        'h6@Mp>h8l8C3(k0I*F`vzl#LOsQ)IpQ7%dD7G>XDcrBgWY<QzK(uWpdX{}vAGJHEQ36nvcJZD-7wx>M{k5-'
        '{2m3hC~Y^gHJ*Tek7Ith3{S)c^FR1EQPQ&C0evh{Mvcz3eEvEHSLNx11VDem;Xcwy*SBOTy+~|yV^xyXnFmhc%#N'
        'hIGs*1Q%Q2swF6sven5?-'
        'p54x|yq4=o`55E*6)v_Qq{}njDJWk&?n6L(aBIcC7V>0k_EcZBvN;H_2JToIf*@(k{pGl}xge0?kjBMw(OHigH8{'
        'JdgW%vwKJ%>Rr0A0s0`D}3Rxrep>Serr*ZirfipHBEMSWe!Idvr!TIg4s0QRhp$s^E9)5nZ+bd*Z<|IT$9nkDJUG'
        'cBs7O(iojpnY)SZmo650UQ|_{^X)62e}_I{q?}?rQ+UQ*0v}ijfyHN#G+^#SNV-pOXJ{b)7?Rtjz5(Gj>klHCb}z'
        '+q0p_Df8Z!ONLv;vMnS7A`G?EdMe}_~<$O?uU)d!M{U~y=r8$-'
        'wWJ_vs%DFBuqN(unvr;;=v{B0Wzov%;%y*w=2#s32lBfw|'
    ),
    '_portable_underwriter_79773e2a0116.reporting.movement': (
        'c-qYx+iv5y_1#~=HBdmxDxM_3JghNZbb$7;MNt%eF${sRX-'
        '61|(o#~!+G+lM&*7aE?Qyy&w!vU5ljnZpIh2>n<v&FAO83)!Pmhey(@C%s9T?fSO-'
        'Du5x4b9qku>dr)ua>bQ0<4R<*@L|8pem!a=BbAj-qWySsuq>6s#;s)pV^G2<5yTD8l!Pg<fmu@S@=NZCx`-'
        'tzXgSy+QgL?YfGe6ihWRF|=*no869yW;8S<$S@(e+5gNZ%ZiUpHxb$s-'
        'Ypi313Qv(s91@bmS0(QdKuWEe6Dz(EeQO*(t2e58lYGFK!u=FA=ee?eEm*+a7kiKDn1m8oZSEH0j?zknCNrgS0_$'
        'DHPN1{1}$tPAis>14^_<w(ji}~;iVl1(sy+=45%3cfLco@&5bliUi~t%0=T|1(KE6^u4*w;pal^O+`&r?viX-'
        '7S?(cg8z@xZy>CZ8WE#5A^7R|_S&*jUHRGq@Wdk3XB9SY4O?Bv6&|i_-k4--|S-'
        '=GBLLOEh$z8}>VpC}wFoeWD)@>^?WmEvSq(6k1D`b)9E82tq8Av_k31a)Y>N2xbkcUEh3#55e@MRI9Xd61Di&j({'
        '7JaKBb|%*9_EgsFmDMW765$0Q<cE(8o?+~2w)KJB^G?MR5Iz}k;aOA8_1;$|U<=GhhfG1Pz;&5+)!223eR?+g)lp'
        '{Xs_OT3+p|p4D-;@->bWn6w%$Cl`^TqTN#nTQZ_vkfQL*~bEwaOj^;&Guxug4-'
        'zV^<K#yj$xMCch6`<EWlnjJDpX#2Rnf7}(?8U^XA1KTVG2FFri@1Z^k!;zi4Od}#5@Gw+%IRw|!>LKtda`uC(Fw~'
        '59Z2>Xq``;B2s0YvVxq@7u*2*cmh{$JU;Z_`^&j6Q-'
        '6WYM0_?L<wHp_mX&o$FpOK6ZwfdHC%*vj=?0AdS(dhkKIwy$K7h26|0b%^P*I$r+}t*CVM4XgqXD1&vG=rYd`h2v'
        'gC>Ohpn_TRTcuv(r7$^|t$CJZgo_D}i6*`NG}{JrH&xnY2_thT8Wlp)KvY#8Mc4EeL%0-'
        'Hz*xfACCwA>59C2cr@2MXYl+P&lF5i}r*#J$JHk$Hu4o$@`KGsZlFa2Al3mS3Kd`xX+OKoN}t<1LgVI<y$ovfT8)'
        'Kv0L$-'
        '9^08^~s|J^?mga)~JtOjnZ+4{+!35mEY6cN)YM*pB_^ikG6Fx_pGjUOL5l4J&wBR!n$Bb2zF3*zU3OS+l!0CDdAW'
        'fAXN^j+N2wqb16Fj-N`61;}y`lYQ{$DSoYPg%<p^D(N$Odu*EiU+YbU86wD%N<sDRO^|03U8Hh-kAPmmt#MexrKr'
        '1Wxprh<Dw4e@F*{=QCN4<<=;I}W1R_<sgdm$hHayt~$vra5c#qep`c=U+dwU7x0prPepQjFDZ9y|T_^LNDFApovY'
        'evmO2G*y-a9w==+HoSzRYyTw+ES-$nJa+=nbJcGie3lw+<Vg=2S+;8^5xZ-ylLm9KaH-Pc1hFR90v(XI>LBf*wSl'
        '&w_m5ksQ*!SJ1<+~^1XTY^2j22unP@W%>7au3ZT;#KQUZDbytU+Z`5X_8fH?x9X3k_u9H_Gq+NVVFTky1|(ECL)2'
        'MGHX8Ye!oxu7=et&UMr`7%R6zQo0@yO?rTi}K_~lIZ&t%yEn#vOt?}!8bYgotLsay67e!KA4)7W0zaZai$s0pT38'
        'JVWP3{(N`n^9i<myhMrE~C>!{Yx(r?dE&CVf0p<wi5WS4=9PMr!d^(AWm{Ki`oGND)+o6;K+sQPd9~u{Ad9&Ywju'
        '#`RNMuQ964Osej{8ARko3%SOCh_9>&53C$Fba1--0hYdvoy@CaPCPq!{;DdA-q~<@H45B}{kW772y5cNU-'
        'ykSfoRf_jkqW+HtHxdLft3L@4*iTjrOm{SsSx`uf!8`=TdH#t9Gk{s9>^GIUIZ-ttW5R>t-'
        'Vc>k2|Fx|7o9={u7nupj=+^h>%u}K{GyHE&q;p&Z>IE}RO3#4CJLy=@PqX%R8<pfHn+3W%G`1$Of$p8Z?ga6U1dA'
        'V=dIkZ9hjkCC2jn+;4h>*K+8?C2Y3XJ>uki@UBC7R_GN|3(EnLgA#{+fy?d}dq7OHs5=-'
        'Gxr3W*|%^c3x381CNYlJ5K(;I&_hr`OelVFA2~3)Qf&nUr5fpAbD=5H0?cn<h#ZosL!l{+qxD`gHq4Cz9Z5^}FMT'
        'D{`N?xhiw^6O?}e2Vc4YcBPz{4qtKKsE=81{T+JVNpp=LQYp{2b(KeWAhN!j!&2iArT`%lDv2Q@u~5(M1VZ_fbL-'
        'r6MHsk_T`@;U!NxO2lAa3*x2=t{@h#<cCx3T}cW2?UnXUL!gwt4_b_H<<eCh5I<9l5%a;`^=A?ht%rs~H}f~<nnU'
        'R7V-'
        '?N%jE$`8@b|JJcet+`9%^>;cmu#im9nKSiz+8>Gj%Ok1Vl4ocHN3`(^<tP0T1{SlZT{OeYJ$W?O%r{P&`q*%@#S$'
        'YOPM>hvSf0z8KC>E|c`SjM>_~FgoZx9BP{!=B2#XHhweQ0IbveD8+H{4QG#ED1t`LO)vzFLR4`ID>cyI1;DczDXi'
        '8}0I=YsoVr9=36SX|J{kF;AAi&HkO83aN@#WdH=o;6rCyt&1@3kRetcjW$`ev4%7lNcH`h%-'
        'q7CN<GTV9N$1rM$Fx(=mazr6-'
        'd@fz;uf75^_vyxWAqzlYVw>k@W9J^Z2K{d8SCKa4c>68=3tbbB1n{W7wRtJBYT@$|U!%ZqEhFHhwmPkirxK$cIkJ'
        'X@X@RNT%AqH3J(qxK?4>7I7pYobdtLRwIrHE+6+^-'
        '{w8P$6t<9RReK`WFYPcl6%2{y(&`sV8i2y$SuF>WqMjA|`+mY>&Sx(7)J#h8}+b;YM;}4}h-'
        '@Xn#AN!$if~fmA&RI^Y`@{T9AZ@20W%&$pi2ww8PP)$J$p<jthC>KXYrmes!s(TZ%Tp_;KD$TK69BW-qK0)J#e2d'
        'Ik_cAl2@Wsi4f9LhF7{E7V$fO^OI9cU@J4?cqdWmF5DUsGw0X0_8-'
        'C9lkAxiqJGe36T3(#xpH%(QU8ch4J{T@jXfW#S>F@5~qRO|EV*_@QdZ4;%7`YKLT3kmeo3%@|2;Tr-'
        '4LhVnx?H>_P6I_zKYmo2Xls;%gqx6#M=O1M9QQ3sYqGUO{-'
        '*O>}8(49{)0Qn>@*Yg|1l)~T*G=*kHv2*Uyoj_>!wU>fkmB3q}H+!AWX~WFD4Yo;Mp;-Zorq4X#yx&s=-'
        'ZXFbXCa`?<nV5GSJD<o@6MBaL(zW_Z^|;#N4oYc1Lm=h9ErJmJn}QoyjP-'
        '|eC7LVi|FVcN7DFntcUeYMHZclWS|3kv;LLsuV&&r?+!E-16~doB>%^2HgpT}6u#pD;kF^M-'
        '8LeIawRTnW)_IZ6ltiKcp5C(9E8Oq+zZCmaO>t-Zgz>T?6dd{j(_)V'
    ),
    '_portable_underwriter_79773e2a0116.reporting._underwriter_html': (
        'c-rl~+jbjCk|6l5uZWDw$^t3@2&6=%M2S-CmYM3JE-R_BDx1Xv27v$>DG-5<07xR)IH#ZX?7q&-IsFB@A22WT-'
        't)d6QD3rV<~Q?81On8hvuC$2DI(n6+}zyU+}zyEJdWdc>15m;=F@qSP18~I<NKHUQF)q9Ceb)AqWNhWEvBQixG1u'
        'DT0})U%Zqt0j^i6Q#zlS>4F==Id{Lx>L6n_gS(Hqt`8=6t`Lw)oLw-A*pH0-'
        '?zm)k@v>oP?NjjvOz2tbP0K80Qvut`I>WmlD;XKbLr7E2ii@`7%o~ELFzQnq!@bPph@#+m2+JkbwoTM7W+vjgyzk'
        'NS=^7!5J!P9r|Zrr%>4;pIgEV(SRU(>y<_Ki_Gjs~+yKA$WHzm%<Z)O{G0^J4c#1pfmhc$>n=r$nP{TFw&~%_w?9'
        '^`l}joo8ohl$OI}2A`3b*>nOlj?%N^bTk62iHrz~Fcuy4^6{8zNnB6TxkTX?ASYHXM6bM{)$YN>Op;;RiXYr8heb'
        'A<$DJsC@VCFIUu_sAj;BbGEEaKaa$2)wImwgJuA=?{477vvJoJYB9Py8mlanGnN#?2KiD;C}6PWyw{N2qjke`6QF'
        'zzUa5fN*R^5NnvozC^x)9ElDLB%~{jNWK*HY*i29Vji4xsr02WqaQzlQQi@WjafWWS$r0UMue4ICtZA+X2?1-'
        '|U;A&^OrRZ+~0#``dTowywuWs4LtW1}i)?71CgZzb&@=+jnIx`m?guJyYwRtR?<C&*qa9MuOAR6KvFiX;8E|h|kh'
        '_f<%uG4`QkuAGSNuKQHomy7#_Vq;1YFh8}}wub=+;<?~nX4I+bqToUhJyx)I57ywEHFod+OtCkN{cfN%izS)2Me*'
        'fpeKZ+)NWz}}{=JC(_uOC07MshM0oo?LFqX9}4z*7&t0uBSAkP_V<-gtojM3ZECvKOb*7(b-'
        'R=pnR!fb@%or%6$!^SyX6A9wG@reK<!rF-'
        '#tmR=w?#}SH1;M=|UA{)(5_eSY?HcY$pqXQhC&9h|Eg;|<_=n!Ctgb!WXKDa5qV+|5Z4{roWilsMYv8jlIzWK-Kt'
        'yo~?EFEU!YzU}<tSB=Sq_EJUc|MEsF^MH>Db9-'
        'Q3@V+cWiR^U%^Ql^1d0Uym7Il>A{%w*=^0GKJnbe$nv}ayJWr0xIEsl5mp~ArO?*GtrpPa#NwS#d;y-8E6y$2F--'
        '))yMO(C4Sr|yLHV)YJZX}CTPXMcXnr0`b^WErne|D+9&k_=<yU}@4w7NhY;G*tUJL+2>wu8NkwWj(8RK>*ZVrQ+}'
        '*h?q6b@%+Dtvbuk(_%cyFLtBTY&1%z>N{*{d7)51taXbqjG~J>%WkxF%V15PFXV9U^!w^Nw(Xi;V0yAynU$*e;uJ'
        ');7}9Pu%`b{%#>e$LHLtJ{FG@2oAe|i8_BJEkSyG%p(Ig$u#jFK~bGDen%CitmCfUh!H!2YQ5M7Z)%Fvu*!F?aAe'
        'rS^W4rFXgkTu{@Rs!EGkrLB%L$Fb#K5X^-zpv`5mke>`L|3LS9L;@ayt8DQPJ-'
        '>$EtA?6Lf|g);)CGfPYf8<tK+2bsX3mcmrbd8>n`JIXxBxS+>H!lMiDVf7x?xJa2tXwO$#kOu<jjiEq9Oe`8+?{j'
        'WqBu=9A<&o%r|*eXGldu>lTMOF4`}nW8ES{J{vdwS#M{qCpQT!3qvFyT_Ux2>EizIS;u!`bsE>$#h=PL-'
        '(Y}7qdoG2~F<DPNKwVo}Zjd((dsBCUSa^6j{=p6=_+fqrG?zN=kgFF+9!-P)fTN-'
        'H#`r$EXgDli>#()O5s)yJbE$Vz#Pv#aar9#(HUCum9lc0~{7-'
        '({k5Yd+O({ZQ4%+ig0j%Z5)(Y(R;gXQFDt4X^Zlp2&VJlX=rSyR!I~-%jkq`QDeD7W1-'
        '>kjf1eSShc8fxhlt6@p6YzqEcX^A_Oc3=ZIh@jR)6Ia8e%{x>~&&sSu)-'
        'qY6QWW7qjfCs@$?rR)m*nf~#Ics$96AMSq=)YQs^%CpO;%qQ7MtuOlCwySlEWRxvRwFbqn?%Akj8N(TG42v;HWW7'
        'N27(=Ls^|2~Qy%J<E?bWnngKYKM*R)-'
        'nfxfitjte*;NXc#15rahQK`CUTd~pnNaFUJZe)o0!8C<3)oPhxFzt*DLSO;H2IK;LKdOsju4vTz)^=dvEUD{$b_*'
        '_4ad|;w;+S6bkK~5|Qt2M}K?H)hcd+c|2_}09x>HJg=TphF!g>3j?sZjhCSY$+#q7~$P#^_MV^ziR79<>{DES|$)'
        'FiJ%#<VncaG^Y8SpJ`CV2ZZ2%?^Y-|wt~+OEL)}pDGz$;dbfkeDIz7R4YdrTCcArSPxmJfH|1G-'
        '4Px#LcN$h48G&Da23rrR*qtOL?A52)WJG|~kd)fnzi;hqL)Fq@Y+K6X(vrrCfPTjpo4^btPQGx?eZjeJfQlw#ZKa'
        'W6-`!{jCi#wG-rt$ESR;No=ZGSYr<PSBM6&$v?hfzm+#A;|#&v>+mrL@RE}IOeser15vb)>8NRK~c^RC9m(@C}i%'
        'G0(zubcMKofja|9OZq}HTxaYF*Xs9n<IO=I6Dprqg!`;HD}uyLj`j*8;j(#kH>!Z6nPtk1c$x@jB+Q@jB*Bb(7Y}'
        'c#a?-u%u-n4&~TREHU=A5hKIIpdJfe}X);l3Tb(Iku+VS0Msr3Te<xsogT09FGCpijO*T==-'
        'SZU4FgkSL@mim%?wNzg?Ypza2Yxnd{ubq9J|&%RjS;Y7=lnR69>>C7dPa{jeN~}$y=A(6&1K4Q9%oE`hg84t>An)'
        ')c><*x;O2TvBm3nz&vC6-'
        'nv`a96cfbi*HxxuUu9ZkY1yS)Kh+6R%Qk1ii9i34YV&RHmQ#Suhse=H!a(6KIqH9`)b5_-'
        'g42KKbmn5R)!V5AhepapGEuNCsKTNqfjJ)o$N3BoX|Oi3If#mWZ|jz6YDqBQbx_ckWM+1n+^%SnUV>7;C{Pn3Gop'
        'p2oJMZ~RpYaCUSz{A3M~BtrA@72b{hngl3T(UgnC2U(;h0JEABVyj<D1v)8)l!TBK{y>yFaNJaJC1Tl^4_%x2w0T'
        '+Zv|Abxjkb1OUHZ8s4?4OhwbrxTng^d;)EBAaTnkaKS!>;J=9I?9r$Wu07ae}`L*8gjsl*vtf|`Usjg!svLHRGi>'
        'D+vgXmqL00r*E`#N2YY_$r-iYwS2*U3Rn?H4YZ2aThwH8uT10-'
        '0$Un@I6KpGH{PAtPrXA5m_kDd{y?1tIkifg#4s1@NrG}w(T(0a#_L%fn!$ap;nW4_jtmv}VN^gPKi;?y~3rq1DkH'
        '`KL+4jaNb6n6MXDuWy`0c?2Fs`t?G#jo_3HtogB@87QVN;HZ9xe(8P!K!(w-'
        'go~ha~d$w&U=TzI0l9tpQpsU%}Go+Mt=W@IjeQ(`k6+uWwx;HfUDEt?dg?ml5ix##?mwpIuNwS_kOwA+f>5bJ*@w'
        't<O%Qg<E|g!kAZD6Uv&^;vvT17?W86M-'
        'lAyzTXF0G=uCJUMhUoy4OED3oi?0^D>{<a<;iW`;|Ux1I(o<r<<@*RtQ%$BnQfN)*e)i58dN*oEIR*aP)3jGA7$W'
        's0ieLHiBl!c@F!BT?2o0ZRpA5B3YKfDzcNB8dhI*GYIF-bT5{M?)b1%S!JA^fZ`PM*={l|mklP*RUbBBzP%V5lY0'
        'us%%NnJFbz>XT(^?>d*W}h?uk7v%n(g*sIRIeh3UPE4o+#o`sAx+o1Kl-Jp$T<?e8_G<|z7QQO>jRQW+U{BOz9f)'
        'A>c3vUMSDFz;}<($U1b)@Nr<Rkr4YTB}D|n&dsxNj0^)XGt~<$v%Ef9=2jT)H+Ve6pvdj9r{hspaaVEgdtL;Mc26'
        '+*@|?Z6M2m)U879bQm+)Uk>TAGyIU4JTFy{A{cEE|9(-'
        '59R>At>oL{wM`V~v2U%6yx%Sg>Jy!oP$D}*kOY~@v5_)yWEz{;V5&$(>s<iEM`Z&E$r3eefGRbb26LA&631$phJR'
        '0XHWz}C1RIQGsUDh)gmZr_39ar+bCwT`6J(OQC4)pGS%&#l2Ja=aRXbzt2J2Nw~sP*hZcF4opTncszq{$Uce&ETl'
        'H;qoImZCy9+^>`g^&+<_!?zQA-'
        'n;mal`$MPFFyXi>)K%oJ5vpFD>w|_>ebv|G_{*r}4)|JU|7zcpCMOo|A^^voVXzW_PV2_BmP42(vX&96wQO@9s;~'
        '{%hJawDd67&@P?XPV>JZJd37KN+j1dG&Qm+D7^(6I-Gac$BXvx)^HFw6@fXN&A?Nr-'
        '&oc?{XqjqLgNsV63^?A*b3A+V+0$!?i6sS}+n+!#}3#@e*Xgp{Jac$KRw^2Cm2thJ9t}oj=mHKIMmP}kq%q351UJ'
        '<xS4Vs*F4TH`L@5~rHy*EGKH*#|FWLGn7PFyUMT{yjDGqO+{C6?Qe`EA5i^;T&Nf7a>?xi!@vDJzdb&P?9gaj7M)'
        '=$X<aw>IW@rS<UjjWl-~DB4-NL2JFO0*I0gz2eFNW;IRbt=k>v@}cb<Nq79!+6;%9b#qOCuyCd*uI=N;#!%$p*_-'
        'zb00p^Ai10fVtaY!Bvpj;p@`pumydb->x~-I_LgnnQcOT=<v91De!F=fzv-ML6g4eO2G|(egJWlPwO%Yo60IyCcY'
        ';BaCN5e@{mU}VY5QrlOzbc7EOxpu#{a|%Lqm_j|91)2ogb>OuplBRXXaU_!?!_-'
        'bCB}{@NQg}E8Wunku?P;pNEpOp3@8S$q7Lgsb|B(4bnrqXgd(a0%;@;=wfyVBO#x?J=goT^V+gF>t?`M7aZ4dL)V'
        ';X76+e8R&!RDi0+7<>7ePhZ_hAP~OBb29tnACs#oXU`$h=@>Uj!Mx>Rn{s6zM4Yg18J9#koH}`+1R0e~oU!-'
        'jIDMq8Q2JV)KlOA}n%Id2kcNL6vAw^Ud(4y+u|D_%R@7CZldXoh-eWb`WjQ*r!1T;~`Dx@lZ^t1fPM7?J82(gyG`'
        'p4c&r^E@BaB?R+#{;sDN1R0k@w3p<KQvOURxVq}fH4gV+m5dvJwC=LstksBc3|ME_B@26X*TifS%;)f4z;^&9FaO'
        '>`mw|}~Kx^?IL-f4GRSE&THbsJ%Q_v4*k1K_s4i?+5-d;P5t9H8>~2_tg#e2X0>Egp(Y2z>J8H8buTk$v;5m=b0-'
        'b7w+CQmY7Kv*8fW;4E|3i`d~J@$sR}B&O-'
        'C$bp5=(7k&WyJ*tK>ZbVx2EuLL5RHY`X@@qX$+cQqfyQ<<IdR@p@vCu0a(RWIE157~9$c&UY3y9@xJK?!B_(F)u%'
        'gx%fEeeKERRg9>U+be@-~#0NSuSf8AJPH7i?@Vb0*c~m(%TsK44e_+wLlS_!m+*(-'
        'A0a$;mXw(3Dc=Zz&hE*(8I)a+nvGECsow7rlp~A?7S8qEQOlAsiOc5)QH{w2=)HI9jApRz@f3bOFU6BJ;(Zk_%*K'
        'X%CjNy^gIRxIcX=keSdUf~sU4DuJ`SB05LfjL?;hkP)$W2Zs=w3HB9VU0Hd0>!DC3C0L;SEvJe<Dm+2pc6vdCJ<m'
        '`xqr51mFh}rBSO?(bFp7T2rWweiG&)W(x}X=mJ}zM(P;xVx39SJBo~9tvwj$UavmxwFWi(Sv(Ve8{fE~<Yc3e=(o'
        't`)1AdV&`MbJ;tn!d*YvfY#vs+ug{Ul!EQQ{bF&1{@?!(<R$rIiup<+lzjJQH-'
        '#t%ohca4A)sFI?X2|<hfB=W+ziP($aj)7R4+t1zC?5C30?wy#TL3KX6DEH}{}ad_aa5`+cvDLD>i!Nu+>JjUXjg$'
        'Ja|GuA*0p4DK*xFBjUzB#%CjvE()qT_Ttk>MZD-'
        'gf;yIe+WR<LSbr?y%o?^c{(1aXpO+RbJZliKX6PyvgD)Yn@m`QI6&#d8auR-AB7t9@Eyv(rQ{r_0N;SU<~gjR*#b'
        '=`Y6c<$x7VO+d7ySX*Gv&tFBUgYJFpd5uJdGQi>fSe!7ZtRvpl_tT?YD>vbNae<*`Q%`dTG-uP@qd2C5hC-iHJYq'
        'FOuG#(vlOZ!3jBxvu62Q>AW(6juf2C|Ja2N%y5|Ruj&?;IJuYM~Fh1ePFYS!`6<l!JyHM+BYN42v9|Fcu4FJZ<Fb'
        'VQui34AU`3^Lx>8axm;v$kVuo^saVB-C^fNq(Th21DAP0}y=9mz%4C9@EX>`oAmbSP9u+|7eCjOmnTIDIk`?D|-'
        'A{O&S+#G5c=9GO<>%gpY*Wnojfk6PuDubx2QAXthcp&T#pT!Ci5zIKt&bXRA{7wQ(YQH)s(qHhyY4>AObQIzFpJH'
        'ZpJh-9nicGXDi5FL)3My-'
        '$Od+vOakVdiv5jKsPWdyR9f<>5XynsYhf`apb3JGI}&t?l2I~4k1N=P%hUWqsS~{hXno#om#>@aZM+pLscJYV<8c'
        '1aAVpHKmf&l|@W<`uoXDSPH|GoH%k1WQI+nGYxi#<C-'
        'p*NPzk%Hxq_Nq>YudX)Wt5e;pN$?qmt*(>x`4|aLP2;%;Q~^0M0}2fN+7KisrI_<;3-'
        'f_zwR*}5Apw1gdY}S*fRySB_%Zn5tbG|?7xiQxD8XWkyhYgZ8+?=qzl+LA?tMkemn9h52Y-'
        'i=DNG3_`(pZ>;WxW*Y4maq-YgnVcu)Hsavs2pL<uwNlNEQHYv3PMnZRI+3-VJc-'
        '$cDN4iw*F*eUihJUz^RpC^iephb?tVa;?(?wjjo~+tF&$$$J1QoKb7(*f@@F*Q8i^&{dyc4shK7@$1A?yUVPze_P'
        '{sa*5T0MUFEG^dp4TzH(Lgq8M*uxX9iW>?k$x;;t9tM2_t-'
        'R8{!oXci0c8M!3TWghpi*e_meq==wVXe%0f?b<Jx#Pij&G(kMpaRiYi&br&}Kt*aszZ&Smq|!h-'
        'RP7V8yq&FQen~{jk<z#aZgwO74rm3j2@Ka=)~W%BNQ-shewz9L8@`WwiZO8r-'
        'gGAC`zWy^i|m>}kMvCuqbgeZ(ZbwrhpP!?}eG`LG0CzG!gR7?lZf&x0MB^%~xxYqop=OL^+W>Pk`m4k~fptXI-bI'
        '1UGB!(9tu{^~XWOLd@2L64vLZID%6`q0prO5bwUOeM7tw~7P0m2%mvXsGV#A3mN;#9m*ev~I4rHd9_}Si!1Vtxz_'
        'HP@_NwHOA&zV}P`EYGbvI8d4vFbvIf0MKV1}E0@0H{YcdEFlsCXs6A*TfJBkNR6P}cMECCgzEV%Go;nF_yuexieu'
        '3%@eyNZr0s2&5$zB-$4=$)YJNEVDisgk&vLt*|6zAZ#={PM&>*fb&4Wm%Sn;*_~7f-bVceoGZ;C-'
        '!5>iJOj;_p5$Wl?DF*?ji_?)V_?$fC3CMEG}HgY5(`I{0y4(`X_O^dHZC#;aopns}v8zy|I?&N-'
        '@nccV@9V@_HY<ZGR@8mK=T9&^I+y0-'
        'Q#3MT1EIvvTQiBBm}tWO}dha{`v=Q<zR8_SnDAhG$WJ0Dr7UHg2*mBrt{0V$}ve#T4v$C2KRen=K&nSt2&)3fK%q'
        'D)KMA5nX5i3Yvse_JHec{U+e01QY==EAx!%RlzQ-kRP|dhTKdB0D0d-'
        'g@<T4pKNN=h6HkR}O#3G(v49&%h%6=S2o3+)#C99UyueOHwzgD72k#EJQWXj}@Tip!AupIqe*|pFzUu4!)3dvk#Q'
        'D63%evb)}ouasJ~a+e`Nd{TZcNfI-piNUJ^|&6d7E`}4F+#!4-'
        'MxymotvuqfinVl`pXr1S0!aA)SSJ8Kt9!!LP@tsCkr`Nce)YJXjv@)qkr1kbC8J&cexfGui$)+D|UaGTue1z3wz0'
        'HFLP;cz8OdY)bCN_>uEgb*Z?HkRk8=RW;W{vQ23EYU)ovj1MNP~eb%%9?Sn$&9>FR?M4_-'
        'M(fz`l*GmI4SZw)o)>;h4bCsP)C57@&O9tJ>$AWMWRi5fPksJ~X)~{4DovLZVzxeR0Lpf6Td0P<)dEpJ?&9^dQON'
        'Uq%V?c8EGPNY3@g9Px(un(8$9?HuwLLSI55V)Py^&K4rEt0X<1-trmc5=m)MM<fO)QG{&AmVHOIA`t-Jpr{v-'
        '7%U0Aj*^;ZX*an@FugfyQM0rlH&dESaw8Sz%VdthMwHV;b&Fo&B~(d@8E9Al6SS)Iaz>%a6ekDrqX4AGc-'
        '(@Sq&PQNifQ@Lhfc8wetQn$R`B(D1&jq`U)v?@Eiz{`U7V%#e79x0rSucJ=-Q53q6=7zIjx0IC#>)q-'
        'F!;*@g1=2^^`{%NORqhRsa80$B$JV88JVX=BO@G(5uyFU~_}=@PWV}qURvgkYB-nAKVlrZVmAu2h2YGYid=pe3hB'
        'Y%Nq0PEL~&r*5aw3j8fEVg3ssm%i=v<OIZwy(l4kd66%|%iGr%1NlO&#>B}gI&lpqHUIcLNzP6IcI{S~;5T9g5Py'
        'JH9Qi5-QFQv}-1l2se))ZE-{6Yq>8<pTD-@AK}5L2WD3Zr*H0q`g;hRI||(Yqt`<cA%sC5&#-'
        '|NJ*0?Aid#d~V<8*<DaeC?gmn^3ePgL&>3P*^5Z#ViY29`}8C&RR$~(qrSNTt|H%9)sE3jv5dS_eylU8dYW`PeR~'
        'PKqXq<K6kyQkb7-'
        'nonMn&$p*_x(oYFs}dMbZDd>|6N;jShBARS7oQl=woJC}w~dPL9e#x8Sv^CGVvsEm6i4UkMCz9^;{#yIMneBtzFe'
        '%AL8kh)Ypd}QHN_ErKUkrt0jFP6Z@P%)e`sWRESCG_kfH(QLw78SrTWxE9uKREehRQ4bGC3Cj>kYvHeL?y%+0y3F'
        'J#hBdM)DZ}>V?fZxTEG#kuQ-'
        'E#;gNkde>fPt*?;|h|L4I!z8egnsrYItNI{<9t?7`?_cwnb*A|w42N8(@(%a{6UcY@mc=Pz@{nwA51;OE;tyVkQd'
        'nof9#&}%Eof-'
        '~5B3&V6(ukfte*ZYyi~jN5>sLKG9=Aq09QE<a@g$u;pU|RtvV1XWSy;4tXx)1%bg(uD`05>ii%;kC+3wAo7Z(@3i'
        '(9?CIJvpq@AokWl-2vw*ZZ&EVuOSDcl~>J?v0YT6UDz9ZEfG)9@C#&$#>&h-'
        '_f6Uw|Dv@@%4CoC+Tm~pZ%Skev;Ck!}0d^w)k^v>&~t1d+{Of?D=2cyngrRx6cQU|N7$H;K%1Le)#b{blvaWy2Y!'
        '#eErk&m(O3lAH4tZ`P-'
        'L|_XqEuKHh(hII1M6{a(M1oopZXlUpP9bV|RsO$B#uZ*A?2t%BRzg!j(Yc;~KFaOXA_q~o0g@nr>fsl|AFyaQw61'
        '@~@?g7mxO7Ax42SdGWy(Re35r0*61Uc7q${O#kX?_a!r^}pWW_Fw$z`TmO^U%!4f*nj-w`95-'
        '$e&|qHe0HPwO`eswuoUPLl#_x|R>waiup8@wV~{6<VP4Lm<o!hor<pVs`7n96xT*(FU%&eP#Sg5*A}wc73>w;Qgz'
        '~3jzk@o-Px9S}lI3-'
        '*M~43?$Mm*V0jfk#lHv*Ja^?H{ZHimjF02@Fn%f>B!=rr6#h)VR?A<K;K*5rwB$kCW^G$y@$6d~#PAb?gXlv%R28'
        '^<MvV18E(u?S2GHdBasVG6+65~(<g~I==vUr$zMLx1$19sU6MOl?-'
        '%0`w58fVjt#v~q4gofgeulDw6T+uh*urCYHpr8e)nAYbw#^0|<*7vgVdxF^#zgt50v^o{L0(2@0J22NL*}Q}gw@C'
        '~Oq-4wJQDi~t&GY>nl-=~*94(nGjZ-JOI!i9`0{MG6U(X2at^~hoN5Gzc|JVO!iPc$JpgU^_nXMo)M_*szgS*imZ'
        'L|=t@3YHv)DrF6tKT1m`Ws`NSDO$(&i^K45clX|GIXLfRFeHw;r^zYV7ER8!RUP!08TFr>pj}6PSEM06!+$yFrM`'
        '2+v{-)Tj(6m**I#6$`4^5YlGMU{bwq7)dNxTd-'
        '=0BNv9|C)5H6EWzM71q&&qP&^*mqL@kNoX@aDL3C+iZW?R*6wdjur52BrR)D>U9HT8S=*Hb|H@x0Y<x1)bC;BE9?'
        'CiBxC9CQg>y8=&35Ts(sBM$TAq=R<=1y0e`szYxcMPhlkeTq&2A1KxGV_2jh^`r<vVC?`24nCyIj*tk4NQKwOzks'
        '~$p?i3imM!WX28ghGWjcR67k+1H%e1p*icnNCNVa2I6yS%y9AaUu04YF`dj5H+@#<ac)jNRjpN}T^qOUY215L#4D'
        'EkBfag~7J-'
        ';;Z5q*B&OBCUvS7O6xHSa;L3ARisv5;*D!A}nix+MZ5FPfxSSs3p0y6$`T~Y{^%I1Bija02&PjG0aeGO!IL&L}{@'
        'T0g1%`HtK4nNNv$tkD2d-LU5sc8BP`>m_k(xR_?#hAhDJq7w(K|80~hOWl@*-$vsy$v2&wa6Gp>-'
        'L)LekF=;jLMAG8kiKKbNOkzHLN+z2CQ}Y=GUE*CjmqTmcx9T0|muV?0k-'
        '}jYFJ>d554EN_zU74+SS;)g^*REvSSmH6>;eCQ{A($ht`O>hd=p}u<>r?ob9kKqN&!fumXO64W|Vnk@eeE5^<nfa'
        '`wp~xl?NIIn{GL#t4E^BLI2Px*u@QzH(w#=etl)(zmnY^@dW!uvS4$3_xF+n3r$lS|A7r91r`}Go-'
        '!n5Z|#iLl(jXRP#wbntH3g&*<!2Aon!F~_Fklynz+`3l}0uRSk!?_q<Ce$#U|N~L&>JI#T=pFu^)iY7@<xqd0k9K'
        'Cz4}_8Wv2V4hq<orkY*aOGcyTm<44&D}lLyEn{KqgbrE`GYi@=O1BN60gNOx;EomqRRCj7=czjhkz7A5_Ko9B#FH'
        'Wnd+ZpBpfLpr0<udk79|HPkw*}`N71C{=)ozkSc*L$FIs;%sJe7K{6jlLp$XIs5J;`>ym+1rPyGe1i3B*i<2R$<1'
        'V_5#+YCvK&2W+?MXMGSSweeZ+u2;@n%$KhG?s0vkd|_qU%VG4R+OkIj-(Tzfe*C%4yJo0V-'
        '*ZJAkamluUpzkt1*Qi4i#fz-'
        'L%b8&{}p?*AUsxZN?DeP3Z}Yp1Lf6jgTIKiv22+bc|p?CX$j1M;9@6n41j#`77wlTic!J0yOmeLZ}#j!Kax(okk$'
        '}cnnKheYx9S%`T7pPUiWnrjMTkef%iyPIxE!6Ys^E!_#b(vN;qJWlf7u7h>Q02!{ZT7gKQ&jIfkHw}ja;A{SsfR{'
        'C~NJ_{^1VTqjsRJ~^80-'
        'oh$<!D#2mD`uC2b?5WZR@uE6>S}81pR?Z@A9*hoO5{`l%1;yZ^LYynAc3PzL>sX^`D*UY6pSiFsd6kdnf7q3H}D='
        'eoAfL0zbDbb&nAGRyOO=(_hiUAkVQ;@eOdzh`KiDF2{JqReTtzMngQB<KUs0umX{KQgt2JK}4$8W^&nL-'
        'F9fy%~qV-'
        '5{mgEa@Z7a>Rc8zZ&%XLJCXMKcqMj!eW&<}PT)2t&+s}eUm#0pK)u1>%<kmJWICFpMafx1wRF@S38EkiqqFTuvSS'
        'HsJ_<mOeYRDe2C!hC3Ie0=j%J5y5@=~IU<Fg0OBAi+wx!)vH3CHF8Pb6e01OfOV5v20VJxN|6#0p(LJn7w+(^p#8'
        '!>Qs7`2x@qcAFv=d?rdjo$`vCD-R}WbHV>OJcp)-'
        '+x}&Wd5pJ2Dd8(EknRpwdJWwkV0=D!HvLfq8bE7%m||@2;M0l_26vcs@}szInU3aCe?Y=6TeaIat8mnD3WC_E9u{'
        'ssMfZ5sTOggMfp?Sc>6IG=M%DFql+i8H-(B@hrlBfh7aNe&RaCX-sLL#_y56!hgG;-9a-'
        'naU{s!q3_d2Y2A6|F3+#b&LOh5KuEsSCmJ72Tw<P+V=yqFQ{TKi&A;204OM+klU|c~jW6T!iY3qiCAAAOA!j3OzA'
        'GoO#^=)J<L>AL*?zh?sv=YW#I0GQ#!O`suqhN<+?;KswQhO8<%r=0z<$!_RrykOZJfPE~j%C?aAa4agI-'
        '5=ak=uvflpNT5Q?S`ipcyCLO|##{K>&9S?TPdj2|Y5&j@6^=+&-'
        'FH4k6@@wrYpX4|K5PrcGoMd+}p?b$GRy%R9tYARuf9aKaU**v_?p5Qecf@i7?fkk~=>rAR?DAEtDI26DF=(o4L3g'
        'yv-Yqun6_uuc%PR?z7%>CO*sj!%@{YWC1I+N-'
        'nmX&EoJf^WW2w=wLiQA_KJe{NeMi&d~>7vE9;<zLvAYKGI3+BN$k)Zm-ZHrs1iu~38A2dS<?gO&fRbk$*|Vt?hDQ'
        '{zomPKIw{aCE(Zir1jE*6u<|ooSy>JvGeMnu1l0w&f~W4K!iYlGvbZ6lM1s@G7j$!zvo3#d~z4<669Yp0(o$54oe'
        '0KOU1-!V8bBKmKqJ6I4<m!k2}4Yw{osR1zyjS7W*bzuzNFBhsk}=eBGczF?T2O52>M-'
        '4g;#1IDISLjkLOUkutS@@(>>rG+zo2%-'
        '&i4asIn;L3ro8@h8`(AO_}YP|UJc`^r?Vf}6a9tZNvhje*J^Nu(2^8VT>jvhS{SHYIXIIkl4NRr&S%HhHt>14H@7'
        'oKg@p8;$IQ^U_R_WnRk+I5`&l3clQnARy4#O|5L_jp~0i|#<{U{p=pQ(O46BW}GNqo%&#7FUB(ZL8eAgx9(7_(kC'
        'mGe^J}Dv&GSs_ktwqG6pPAs{27mI5KZ2Xul4fVyZm#oZNu^n8t=2?(tV5DdX6o5C2SlX;?H2rD&idvV+jDPC+I1e'
        'Ab%xtg<jy&eImU@mzr_C3CV&H0KR#Re@qr>nU*c3BJqvu3v3b4Khu&h1IpHJYULIyY-vt3gs_Urf<6*3G)Iwbevl'
        '|F%NcCX$7iA}NgG6;gz0vqCH&d{25v%32jIHBjEWrR`u<jms=FL<$&KiFs`|;2zmStz_D#kQdH8Ws1HDF3U)l1-'
        'ezlKYC}$tWFe}R?9jz<Iy-&IhN}4u2^5V=>6Nl@*<fJ(YeO>b-'
        '?tUpHzYt4dRY^9u~^w`>=Pb<sQ3!rsmd6@t)Cd5W8lQ<Z^2_>UW|g{Bye#U2g9}U+{Aqf3j-'
        'Gav#)Kg_jeEl3Ir(-'
        'aHoVyQE74=C?wHqXbX5MY4=#KlnjNEOzP0MoaUcR*o2Yr~0^M(b<yG?j^pwF(dFB3PH(z>o_?XF8}(o&&%3HLb|P'
        '7t?km0cIWsE<Ga*e0P>Cxhl;FELtf%}O8nI;^Ru)i&Q`W#$yW@VoYk;pIVc&N6=X#gqNB{KTsd^o%*Y!_3J*%oVX'
        'q?fCidsWm1J_Kpi|mjbnkW_ZzAakwioSe_iX}!csj}OSbK#Bz1`@$JD}TPW$`B*=790<;>G)XjxM|Esv6(!Jjr2K'
        'OeUZ#-s^)d_}#X1SYvlDdy%?45gm$SrT#@d1{(jU@YYuzvH>14^$&rY-5j5p4oVp<M~+aAe0@cDt>6#Q#p<X-'
        'Au}*R+1ZH}F~Xo>hA)hkxD=mKAfda<D)PAcATUvYf}DxiMoSDTTs9Qf*%~~nE8I77R3o*PRU(4)^OA(VP}b3ziI~'
        '~oXq=+tafjhAG$7j>!8h=;(|P$ld3@TdOKdtta`7|YbXsOGmsPA~VJTcg8w^p1;6ps3NK2cjq`n(*yVNxhJ61q7w'
        'Xka|sUfZL+EZ4Va=AT5+Gg7hPb8BG8C#?$l@=u9Nis(VEls^PzdpTuNy}3ahknBGO5cTpjMadN1R6nwnFB7lw7|h'
        'n4KBId1Y84Vu0X!q@9o@YmFiJq93Wk`x)A{A;D6eoi&)X?-'
        'X1{)bOah*jDXp>FS`3y{;>IXnEfPVZg_$eOCJD{1V0Tk@iH<n;Q=sJ#0vgQdb%h$)Z8O?6{4(QJBLY@8iRv%Q?V2'
        'sDx@tTBRNsgR6QsKD_eFTmbK)3zglRHm){rp**~R4?f~gq47RkVd>P<Z+1hDlF~Ksxmu@rW*8cOeoZj(u`t_n7Eb'
        'vw-AMjG~&r<M@Ypo^ol*UZEcVn}5^haQ<{#|6wK5(ZX2e2MAx-SO#t@xq%R=AsyK;}cK>b6BNx{>K@YuohVO%(`G'
        '+?p$UxA)9T9!kPD>Tjc#a59CSFRAC7h5(lWBmCZpw$kp_b{jD>yT7wDF9W>@qp|HIVY*zpT{0qgU5fUO*%%s%ZD}'
        'SYuv|p)G(>;%o$2W7E1|?cisJnkZx3I_tFN!hOD*qp0K|5C)q#?w7W=&9sNMSoKDXisZDGpe`uwEwM1uZVsHVVv$'
        'n5M(aSBnYqjJrp+TCP2Jk1L{{+z)<NL*z2dP?kWNBS8#!#3&@Ukth$EFbl^(3Z_Fp)u<@wIW5Lhf%-'
        'nbF+wJM>)s91f-'
        '(TQ!oFbltC^OBpk24f~qx0&Rc&BhDh3%<a*#ed<Tkr#KQ_oe4G>|v50zL1BOd?$5arqxk7<bi}hHxJ6vDBS+o6hF'
        't!O-{@rcMzA8y!%#EPX2%3ct`o8b48M9HY^rxVLbw2>@@+W0d_Ek4mkJMYXX!8K174&H)`vD903H1e()HCc%`5z-'
        'aejuj?X+x=7iUsCR5=#-'
        '*y}*#Xuo68<VrkaMFpXbFEazR_S{=%Ec^$RD)lh63uI*whcMhMsRAa4dD#lPcxX%<Vn=3B0PHbl1*PNyHTr>LG8P'
        'N=`r$&i#Yrtz2Z;L=&VoA-'
        '(Kc^c~;f{LrlH|JG>Y#rJpi!__4Q~}4!3U==OG`W2w>As}rae>Gwg6C$qWu64y=30%Znf9q@lQw1c^WrD<mr*mYw'
        '8sOkLM~~e3Hwo{3}q<))f4GzaAxJgG0j`K@`Tf#%v{wbgJccb<4nzv6VeucBCGwXTji9ebDcSGso6pNT4qb6&kGr'
        '1)9_O8Z=t6u|uajV*JZS18uB^DCqY{)-'
        'B;Lrisk6;RoaGA)SMa_%<U&Z=CSep1lRt>O$RU>uzT=nIqj48tF})XkH}K60baWqoX3nfbmxMp0*NE|7a@OsQXp>'
        'h$&>Me4oaPirI4|>)X}qB^(Swyo!e>6-V2@FaLyXb4ULD?YF-'
        '2rS5#`*zm1)rVuc0Mmw%jg=`Lrt{vUjoO79+u=ux1et7IG{hAtf&Dh5_I&SsXu(Hn~m|V;-'
        'xD1`<9KC9A_%?C&fwG5kI_l~?@Q<X|rajDK<>|l4wA8m(MEw=cpnS$wH$D<=v-'
        'CV9n@WFI7JdR;+^*J>Z*w%2x9sr4(|kb=!Qu0WwzPx}4!6-'
        'F`rZBY0>pGwBS(}IR~Q$|1&y#O&>>6)^8Yak8uqrVbG{iZl;F9iZTYWVO8Lbs5L|v$gSlU^`>ZoTAE*%@Vic+J#1'
        ')@V9{BFWGU-SNFa{<2BzPEYZR5TmA_&<>-'
        '*H;RzE_Am(mVxb?fO0Q+X(aB_+l`+?AFOdIkrbaI7XKF!9o63Uu2RHpUX)$Ok2?9_IK^o-'
        '~aXhJ|a&<`&@`(RCLg$aoREVvEHWvExl3Sx*JJ_TMoN+tHx2o)?BlfV80s)u1edDzP;jvZf?Z6G|EEUOl&bsw%43'
        'dKZ%00y<JCYPYGH&1G=HZPmRsp_L&klw=XK)6_i=eTtQJo-~WJa*5&n-cW=*nsZ1v#eYLptU)>xlqrdr0<vh?_-'
        'iC$Fq*4+Q#651E)CbBI&ZiC?SlU-xva<tGE)VN#kI&1t8~sD60cO|5fe5fU4!r`CQ<Z7UJIqg93eNbc9!X8uR@QL'
        'O{S7Xyl!G!sQGBRTzw#0->xnb5d(|^?zoI#%i{D#M&8qgedoyE02l4q?sO#_-{KgLC2mCVtsHq-wDYPH#KxjIbLZ'
        'zV|j4T;u-HX$##B|=y!E?jzKyL1MU7F*r`1l!nmE&@{-'
        'DtEc=S#qL=NP5FzLIwqVg=A%COEy$#<cmRgl|6D)PTf=CZ*v(m0*~WM!@qrXB7G}ne0j-'
        '?2&1;#^|KwF51;U+N^F#i7Jyivjz#0=VK`t!uCWFILpYc9B0H=-'
        '8mjWQCV$Q*tE5(Lyk{Mo0E<P0SmO&`RQCFx@^~&ob{ch#I8#*y?RQC%F0sl1gK3~p0ZQm#KyRpCqqgn7^=Mmm4KQ'
        'n-_rk;SG{eI7&i;D1QC~15XjMcrK#S6<Ion$0x=wC`Jzl^{D%&}WZ4{4DhKTr*P#S3P88oxn*tGG&B`D&9i2z3tv'
        'MztmW1UZXy5nNBLJwf(E4&kubQMt6WlLn>&@bLlK*)VmPOca5?Xmoa><plikOgMR&7UEQK$Ty)l3-'
        'V*EYG9EqqtwZ{)dpk{3(r1=q@xLo-'
        '2%ioP7`m@b7N?aEz9^>sfqmm|s~hmf3uk>@$uF`lEf#$SXLG|!qfi(;1!t)as#DABfN_FymC>i5a!C7Mt3Hv!4Hs'
        'e~P7#gKxFICaHGa;~&xB@lPHYs=$eH@by}d`a~qNp-'
        '65^_5sDB2PQWyh!{hN`>G<2SGvQj!sJsvThYz7aQ0W2w}^tphJX1kY)J7o<3Gf2{d)WgF!SoOF|Iq)5t=Bg(nkgd'
        'kD(7X6?uMa8Z6X?2adkVy)~It=C+Tt!%GhHTwuzc<tNSM=+-fenpYHeb=*1QQ2Ra3+>jO{(YXasp`-'
        'izVvT$5YE;dft%~m5__q?i(v{~T8-=5X#0-'
        'T<W;d+U#^$@cJEfFiFf?<F1idtw{DYGrDnytCXg?URJqDWrWH(PKa?G8b)(K*9FVJWmOnX8TBqryR=wOv4|T00gY'
        'uv%kwYaMZ!2f{R{T4(@wg$CMOx;QbILzQkocMU)(vCI6@}$&k^%i<;mc^Ur~<c{A1qy}I&-jKt6d3dmW-ZHM=juj'
        'xQ|(ulzs4yo3iVONPr4PQKm0o`V`8{rU)W_>keoKQFXO#6sqg1-'
        '9`*dHA(bU`=~CKVZ$hfFCC(QRSe%@UWIn_hC+>dvqf>jVtgyI+%$`?|D3T65*1tTL6?2xY4q6-1g6-'
        'PnMZ%8(xczKcL6STocSBO(V>KwX`7#$+WnB1-J{;}(MH~MK3wh{7xt~Ibe8)Qdb%-'
        '>yv;q|Sk43@nD7wh+mFZtY4@m|<s?voSwd%XjBaI(F$HB^W8>_LlA4mj^X4e5cbi<r^G26-9d6(;7wxhV-ocU;EU'
        'f~(0)&Aqw{0RM#fP-0!|ICmb6kfgFSl=lB-`HF>O}bFK)?6h-'
        '8S$&QfJrH{N3>0y`<ldwb5W}wE~PyVsgI2QB%Kr#RVJ#A8rrCFYMfu4HP#KaoRb{^Z6+~soC${sq9%C!)kku=Q&<'
        'FFXK8G61#dpLE_y3;#EPWJPPVf6v`CafYnyJ(eJO8yPe*x@#+C6BLzMaBmO<&z<;IJKY@N$6e8%qLf?>&Db%PNA9'
        '1_#DQ-'
        '=SnK~>?8U*!3Qqj9~(pgnpu6~9)8ZOkVLxpR}mDz5!43m;e$)rf!op21?G*EJV%2m_vM3QHvT|lPq$fn~Q`}vSz+'
        '_B;jT47b3K|Im<bl4L;H^yG9WLT_I;Ps`nu*gcZ@YETg-`l#?cENwt*w-ZzGAUhOlB6vwcvdl~G#99!OWOkC-'
        'P$7yv1dpOy^WEj(JsiV^L?+yG54%52%DzyTd|FZ{aZ|I+utkAX`1hd&h90K?e7p(7+zV-pmzq__Oji(6Uh@F9_;u'
        'T4~BsM3i{*|^a%^?kGgv&FSy<P%E=9`N^NYU1l$!b^T7XjJE$|5t=<lBd71qRRrrKFif~x{mA|VQBkg9J7;opU9C'
        'G*BaIbQ7yx(74u87j`$8PWTconZ692XCzsf?oh#SVsLbsHG4|1=%WPm)>by!^wrw_8=)TfmB9)~>xFeBu3|mlj1{'
        '43^HK)?$?25wj&&xjYj&MFNzFBC=}O@>TfmOTR;7*RjtAUF-UIsXX@E0qAGhbWz$HP<<CRNYj<fw$X7+lp#63v*T'
        '0)g>U!)1WzfnLaR(Jquch^^Q_E{C-SW+Zh{LYgkzgE{T)u=Lb4vzQ9n|<I*5|_UsBVmV~#R~T^8vWe$AjRZl{-'
        'h+7r<}W~p<_{%)o7r?8+^mU_b1XyA8;_jc}$nFg*TYCOv4@v7cJ<;Jqt`T0Gfm{s;DMP&qSgBbNgW+rma+;lLqmY'
        'd8xa)su+-JqWlS{0M&C?CT_+-2eyeTp@yMt4VPdYdg)l){3Z&N?mdjRCO{hk`Dp04KpY#S~f-'
        '1{A&OL|!c@1+mGBlEpk1epD8ZuY&Qo8-}=Ywj~PoXb{Nu4qMShUnlauCYSBQFpo@<WxkkOQ-VVg`yYQ8E{fFft|l'
        '_ugv>Ot8|`48iK;vRckiO-'
        'D&IK6bIu|jJ9u`dsEteE%7z{Z=~Sq+<9rIOt^|f#w^s}>Ez`mAiDnD6<(nFld|q2YLLVn**#uwQ>*9NtX}4UKbl`'
        'ddJoVvaGJHqBzt8dF;t%g&v}yF`7k>a&O{QfR&sDf=C5l^GiH?7_eS7=f_L!?Zw4X~g{Svdaj<a+WJLR<E04;{Og'
        'rw==4vEv{QrIIbF&CVJ%ZhaeWbSw}vO@2WKbKlRO>8Atl}o*$0*bgGs8WIy47uU1yQQlF!`E{dhGmzsSG*J@yK6k'
        'CNxFveD0HrwIN{LIds`OpO0jb3i4{c5krbCf`9awj4mlC6ZL3}o*NEauscD^aN#b>G*taw`Gb5>{b9$2&a5xq6V~'
        'a}<%2N~5>36G#uTCs=k?^FkFgD9fn38sOI_m%Xz3;Z$o)p?zg)oOBj9l1a4KHJ>3>0dVa$9#hj#3iZJ6v-'
        'ynv<;*>nO&1M5}H0kQ!X-bw<>R9T(<H5$)2V*N8G7>{75@C_vlFpoMRBn;G$!69REYdsww-'
        'W3;~6mSQX}1IH2M($MkcI?U-MuoMcbGR{d$0XN6VSLi;Z%TlVex;A_Zy>>*k4k#(-'
        'o~;ashm9grA$V7*|B|;vaLydg`4yKyx+7Vq!{3QDH+{YNX*z9%-'
        '(xbjG{Z?=rscd9_vHN%{wHof>e00lUexzw<+2rHSmAjZw_P_8i6{O83QmeED|o48-'
        'P<!vhnO|3MMt{8&G|>(gB{V`lDsMeJr}qoo8YTgUtdv=y)!rsB`2xvG`6bEp7!DlbLqm8N(nfh8_XUnjCYgJyBgO'
        '_5w`VRzdlFU&Yj;-A}}cfoQp9^jgRLI%(H7wx$vt;S>-'
        'W?O$4JmcjWm+Frx%>EG5v!t@MkeC5zt!87KozIv%HX=FTsWZRF_dE6rr&hlHqf1u9Xd`SZwm|M6o&SJkxEM5|ubg'
        'r<kvZRi2-'
        '#v)!e4eh&T9P9PMxN2ukIjq)1v=Tp?oFe%}UE0t<AiN0nGYjWi_BXm*Z+kBYvYZ}v)jNTzN~~CO>n&%I0R%aw8O>'
        'Sl4?FC$Sso90yK$Zrt#0=iEo9tby5GBd_mf638;TK??rs*;j8qz@$$U|yABohrW<tJ=?rw%2V@5q~4nzKDi`cyu1'
        '+8cWCwy>gBdHv}LmHw(?L42uG1Lg+xJeG;8b>tJsz}3nm0!Sg<#YDRvXR+XU_V3ncrpR)?w7JFo;RR>Vxz<2Pd_g'
        '@ewFW9{6#+Q)+a}H^ZiHl+FIXM2er~Fv{M4r(btkLV6&7x(5q1H%k|``p-'
        'l>eDd&%;*%=);zb|0#lp1n?zU_*>&_ewl133b3FsLMg`uXd?Q~-P8D-7~&&SaWS4&%0CZ6!@xz7-'
        '60JMvY{AIS&ZnyodDMj=jmu9Yb`;F@Y4I2M)Q+yYH4M|iro(5HfVesVHN^_jrDdfoOK1w6r2WoRcoCv|hbJs=`Oo'
        'eZ8L$6j|U{1j{*`K@z~Sq3-'
        '{l%fv*s2iuKkc||L$fFO2*rS5B6Hv|P?G)hU#Zs;McNEHtkFs^hW_R?vudh6Kt0T)l&v3aO;z>G}67I?J#i&(-'
        'kv<_<OaVV|+}Lj2gRqJ#1xwP?)ostAmDU(>(j*_!I>U!tPo;yWtDNIv$`W*{7f6Bb!ZET&LKN2>ST2|nOxvI+zjP'
        'x05N-'
        'H0_xe07kR9yjLe+aI^iGlch^zff7S*|Ln$C*+7^b8<Jf$a0>zc}{1GLLJ`4dISpU}oo(+C)pt`eUn7|N@7i&#Cvt'
        '!m(URZg-G=_EVN^U=PHl-Pgqr|0`GetiA<*<k<iljr;I4ou&NWM6uJk*1?8jrka{)9?t7%rjhg%62+jMI%^&xFzD'
        'LWwxi|CmfoJE(g>PDkUbS0w)I)<ciL}zIqjchb;z+68MHFHcTd|lsxSf>DwH<cuTyp0|A-'
        'p*w2rLio|2*Xc!mH6R|xI!DS`Lf<@`~^#d-'
        '$1ecThG~0<P87$^Q<7NIH=Nw~9kDOO<V9h*JbQgP+f>&h2@~~F|8m*R4+sGn7D;|GCon$)Dlhzf*_SZIh8qsw411'
        '!Q|XVTSL8Uo~<FRGy8-'
        'VTJ^XaM?I)^1neB~Wl`18Rh?3xwh3KQIGxkjwSomH5T&4trwoO5Wha?~=3GB$b){*jwsB?nUiya3PgdbdVQ;F}so'
        'X#-3)(mCWsOo_0k;!IsR5t5JDL3}$eUoa{3n>zEhHP-Iwtz$pRvC{ZZjNzAV4$YP^MYV7>0%@-'
        'I9g<Ovh6B$%^{YL^P8AKAm<w;7<{HQ67kg05hh|Mfy@Qcd^7=RE)1#7QG1237?yksW;o0OLj{nf;xeOj`>fF@ZsV'
        '{;Oxmy`s41bD!HoJPsXNs*q=uBp8Q4%;^Oiig2aN(pwAPkPx*`ypM@n|mWVuvmO!4NunNbH?k#cg_XMc&{Dh?c`i'
        '{+CJ#?61L<4bugW9T%Kb=^lE?qdT?iDx)|kyVw-_{L*Jse|Nh_C!@M1Uc_LU#fs>qe4L}a-'
        'F_^DBM!p7k!BhZT_{tG=Ss#z-'
        '>w3^Tb)d~Fs4n<7*88ZNcaa~LAa9|Id9He)wWQ#`hC}$9Mubrdq!aP&rJ?2CJH83o2>TVk@gczG6tB~&pc5YA<dh'
        '%a_d_LowdFONOvE7sm#wMY73;Gt?+e^C>pDsY4SbeL@z6xF*Z{??2YcFH!?^F%9110a*Zs;==Fv_1tD6*9M#UD%g'
        '?<*&wM`14x)%k9E#4HXcn;VlEVVfl$^8RQtexf~VY<Yq^+!GVg`~Nu?O;K5!b%=%|5E(9m})x2{6rSI4ss|hVw<e'
        '1p|%UcQAunxeWiqLOn40;O^Ieh(u9yDG!lE~lT~2jWHvyG`IqL~U3({FU4AcsmUKHi^|nEF8^aYJn5%Ji0_{e4eb'
        'xQoskHEQ@L_cn?o-^hoPeeX`=vKfv;C_<=(^#3UrcaySI?h)-=Gt5-2xihU^K=vir-'
        'HROUN*ex&A!#I6!afZ0-X)yB4En&Yfv-CQa0)Ic0U<$={xkwQeWcAy9l4w4%ViZL*;mHGxr*D+x3WYarfgGrG#>Q'
        '9YYSSONts9;fKbfHMekt$m;VY1M8iZ_^1VZ0Df4r@l>atd>e(TPaw>ioHTtS$5TY12-'
        't3HT#9C65cTw*fl!_tN96b47`0*CcKw&YlsJfWHK2HVqR&Oy=8_Z2agO;IPq<Ypi7i+jEdz;0Q4^123wVqlx}yL?'
        '&0k!p~N}fd>+VVv}0W{Uuk#vc4xIaBkC3<GlEJGdyIx4qBxtuN0dniRts<Y9A`y2e@ncKllF>K8_}CE$SGwfWH**'
        'R%FvV0eYo{jhLDR&mdD69->9hTaxtTcgZ1>Nhkq$|F!FedhYL^@2l-'
        'hxM<vmP@fe*5ds#{Uwj@MD&UQtgrbb|S*p_5QAxW1IwP20|<kB<=!;@6gu)TR<q<JMCC$*V{m5bLd+cgkg3NM$^@'
        'i3c#ZjvP^Y7<O*kwBw-nnv_yH85c`%0~EtChV6OPz@&*bO4wY*?BTt5_piPJ<E+Np=;P_ZeX0%H4O!n*vO|QQeO}'
        'meMl6ItpETwXo?Mg*UZKv&T}^cuO3()^VR&h=ksTS3BdL142%Y(I^{8rM^6!YB%zZ72af@Yj?-'
        'bXC{s+q>QD56i+)cS84p)S=ILGQshj}WknbGTI4~qf&34<H?ZR*C63nKsSSSwNQK0%hl2YDwD0luq=?`YLz>Z#|;'
        '}o{+VLFg{ofQazf%mGN>{i9%$FC4b3ZH2nFvA`!lBw+jNicQC-'
        ';1ief6k~m27tv}bD+EoQ>!28S9IUxJIG2<EXyGr5~v>S$d|AO0h+)EWi&rcBVkdFN@1-;o{`{k+8D~ZB{$3-'
        'GaW*#Hp`0b$y`aPVKxvs6YFX$*!#M6(C1S$6Z1VEpfFsl6P&9FjIt8zpq}tm(>8${Nd?B-'
        'NOEZWTCW*ArHz;iP8z452!f7>j)ZfJ3}zz{0b?T7QpHm;qVSRlJj`e%0)O~N@r9fn%ttdY%V%FitL>_}dc<0&nWr'
        'pTlZoAo;^?ZHiIlg2W-`Xo&TgqP>OcdkKtyPV-'
        '{iGpsD^aC$jB^`eJFuzb1RFIs?OPA1e5w=<z2t(^?FpUiw*t7ckydwC03^rH*6Lq&~CIY1qe;IfP5M5il$k75Eec'
        '+1Q#d4J(2$PXXgl_Eg6iMoscl*@><-E0*d=mwkkorlpn0hMtWOb{W9jxsq6^!4kuJ6GQ_tW=69L9d{E`H$BZ-JnT'
        'ISa%*Ig#BZV`q3qoFcDL!Jy-'
        '!>+0hl8)lEGL=CF*d9)i94Q<BQ!azF(~mf#yW#iN;%%;9;v5GSu`rf9yX<jBTAVs3Vw?e*jOHkk7#9~J2GBHUapo'
        '$1_?<v0oc2=VF-u_e9uHB+Z(DpQs@AzKC@bdBc$l(Bt6GVILf(8dYW)C4WeP0llZJY@}`yF4yhvebW)_SLFD6T41'
        'bLBvx<(MqLFQcYeMVareiIK<9B4ZL)3p154oFOt;u;PZmvt9*+g1R=v8<)BupsAi)##zY~ElBkqF70ueF5PVpc!P'
        '+H$1rquvtdNq&`=a^l(729LgK#UmM~@5C{L^&w@d0>}K-'
        '@qXGQR~{^&gR)tF<>KrtDVE<Spnf@vF`Je%a!zuW<AFBkX?xEh)QF#-i|IvAr0`0lYD7D?4x16G^ip0AiYXT-fes'
        'u6te~BP_?=q5{;EUCBhVrSujgzBtPY5x%W~7&o_<)Pqs1_7wSb6{kxA!)pV7CGl>4}1J^1fne$_cMw)O@x1(?}a%'
        'uerR@JDl59eg$8zp7FZ&tR3pLAjh~)8RZaED{lm94Vu)i=I9ODoN6Dq>U}B%&Bo8>I+d7hHmZdu{cJu!<U;H!99='
        ')f;b6afIP3+NmQQXciHJPc%U^Y8ySbOGpN!);#Y8{;ufAmZq&8-7>`et8@8~7)NR;U!?O>oXBg03@1?p4thv-'
        '$YtcQZH6u#9peK|tHIFd=iUV++tq))A6xV|KEqSYY+tNy{B1`l1EU-0JXy?Y#*8a%!<K9%-'
        '$+IL9ZZ&<nbjI)4Hbo<$Bv>_rirlqKt=!&kUmpY~v*rSU^HMtur@=LZ&bxb6IWDTw10AG5AK;`oN#|=uRe=tjW!E'
        '`@vejT2>Azw>*LTc`)2ei|hMiSBW%!1z-'
        'xhp5bMIOB0=I3P!lp9NMjJc+So>u(u<*##fNyJUI*%PA4jY643+j`!)s*m|1lf%Kh}<&6Gb50Nb}&jYssXqD@Ce?'
        'BdXcFYLY_Nsgpk)58UGL19*S{-'
        'zFefjseu(R%;^cUaD~xNhQr0#VnUvZ=ny;^2(=(Qh{vWjxergI5iB&6=YEMEhDbR9K#~f8%o>Q-'
        '(G*M^9smY*57;b*5r6mN<2TM+PlZ9qC3OSr%j^V${A*!eZ#Ga_8RwHMA1F_=DsEC0@!D@hZ+js%RikUL*3`6)(Bq'
        'ODD>Yi1jLH?!^0vv61P3T9KzB;d5)3atw2jAVurC;m6~DRjq{hJ<xcJnhQZ3gAuGY%5pWqx-'
        'I>L;?$KgwlvYmX;IWpxEjMarI=#R(@pokBQhO0i|pR&Q=)+n~}D}{hFt#fb+I~!<kyd(8#EgaC_LH!#J7(5P#%vO'
        'zo$bUHid5nq=of$t6=Wh+XhUTEZ7nz6`?#M^e(Ke?3xcpPPgrD?Z+Ckwjcc&q{B<*;ZbqO;p8Ow_k;e7Cq?_R&^m'
        '88aJ<7Mjrz8_#8!b{-'
        '*J32fRo<RqyKlpIN$&@I^Dbb`JDDl80`*2CRw!jT<$6IdS7|MFsZez9*H1@UEZ@TXU551>s12kD3I{dp7!N44vN;'
        'H5Bl1sqo(n%iW*I3#$ex-'
        '0ycb=$?64;j%3X1tFq8M$SF;UD7Z*VS<YIO*^rInsfIQk0)O;E2wt&_6uiHv+AAD>meb;z^wQMqT@q#C~l^Y-'
        'zDK_(Wy@NpgUFgwNhf%IoeR49V|>e<#w+1QO<yn6rq?c=BKU%Y-'
        'bc>m+`w=W;>58gd}y#L&504o=hkXXq`{GoLMNw%zfb9N>oi`-'
        '7qLX={d_2^g3({h?$$b43K$wdgAVg42IX;$RF2zBCD@oBYM*_qi+PUn>5_$oO&&PV~oOfVfdv5&_9kYa<kaSbj`P'
        '6ehEEbL|>kyNwOiBzQKGMUR+x->C8Mn-'
        '$nv*F}?uBl=4r!I(idKZwXUez4~23N7RP7d1M?H!XrixTqOy3@IRt8@FiPQQ2SZrjVI<?};b3QL`z`Gz|k_9Ak(O'
        '8=6Q7P2(`wfzhTr=y};KFMYQ0R_zlXGvM|%k_hPZ-*YX|BjME-RmEkK!399@Qc0rgzi2s?INZXYpI;W0bw_ieNZA'
        'M`M1o3Bxg!Yw@N!)H`#95L-)pRJRXn6J7i@xInPw$S*z}LZ#%;DPA2iJF5afpv-'
        '!L#^Q@niIJ|Bvv!8B<?hse@&MW3&?S}cISR-'
        'u1bhk<hIN!5!HnKg=wKikzwi_B;$TSTNVThP17f6HcmW5n(@ClYNshBDoS9tT43+&1AX-aN!o`xj4kktY<_K?OTa'
        '|!6dNQKE)ljODUqMYYv=unIf;UZKGJHWs8k>O2T8+^t;^w+C^_l~$7um%=XuQVV@Gy40`e_cZZeH0xiCn)z;p`+c'
        'S#N7s(yADL4F#gwUI_*!O{P?PblrBc%(?dO!&tX?F#IGGj=-'
        '=EHMnWN<1~&~q3v*D*tJCnBXm?QKsdE#6rG{wG({8V?G)3DJUY%FV-'
        'g!P*$aK%F>DJ+z)X%PPTdhAD(ItVU>nl4Wv2xjw*N3i1(@R4xBfaR?u5}YG(4(D5t?TvAz}T48Y@k=+;1VY2*pA?'
        'YrF!VmekA_nt-=wiG6<Oj%_U3TEF{vUn<wBa9yH;2O?yv5G<-'
        '44oX*^XDURvVyL(tx)D)L)Hoo#I85AjMflo;<1M$4ZDU5v-eqim-'
        '`piRU90Hk7@#us1+Ce9vPJFUQA3|dhH2kbjK-_Nf1VnR6G<*WW-*Rb@)1E8Vp6BOfZTN~-'
        ';<7?*v5&kxR@p)HUaK7mWWizMhn1@5Pdw-#rIOImL%U{F|E|Gy@3u}KUZnxA-_UB!7GGZxlIod(I=#W{bjvTk(`h'
        't6;<1C;jGLS3`%jXhM%VxB8>7FOIhj60vUgcyjh&Tel&AXSr^yn+yHdzQvQ`gw8eeU)?5le++UrNG^QspL{8wY-'
        'a>sXK)Y@LZR9G(W-H3T(R`0Z7A)%gFG3mmOcechmcLVQ=-'
        'MPKBwKKNf6|2^NjjsEfUG_B!?yXS9<xirL)V(uey)sh!vWQG`UX%M&bj=h*%?E7{kbFX<2AcaUi5YP_;A72L#d#R'
        'SJO)zn0LZGsRB}LcTYucx7un&eZxya@$VYGC&7VcMOV1+Q6VD>t*`{X^zPnTT_JP`Frz-!da~>2<u}A-'
        '3eGftAmEPnvgkxILK4&&~B|&GF-!z?kKa@_sK8gI@emh=;q|Vw)8|2F#%j~>M*<(?N-'
        '4;yOC#Ku(v$z~;Qv%1h@0Y2EA#AR6HNT+MB$V}k6?g=*4))e{VgDM0-'
        'O%2%7WxoYW03&Zbcw)m^63s@ss8v?ydq%V5hdh<D>)a1MKDB43OJk*SN72?T~@x3!*>ow%7zM=P|CQILhJ-'
        '@G`)=X96FsT^?WiNcCt+C=7o{%kf#Zsy*iHu92!n;_@R&B0~KE8|Fuu}(EO}>!KfBX(9)Z_PWW_<0t{}w(b8Yly;'
        'St6sIZy;ha<O$yG1My`PS-Vh2{=NXf0&}HJXUMgy60pjhWI5B@a8Udw>-'
        'Kt)GL!Bm(lmr~4ZMq{kW$*qwQh7>CBe)}~+EBa?a7?0PSg(R*ZDB6ITAN4zjbk3*!itEHg-'
        '#Wh#fo?NTQoWv9`7{B!%g;wI$8;x;h4lqmi63%om6L4_Nh8ek9Mlnpn9Mo;`GI0&rY1$kk@Nehgb>Wp9SpoGJEFc'
        'U)4PIQw3>e%5(ZnxITgjU^@F=iAw{%0X5b7sz@9FjM(R1#d%^V~e-'
        '(P5I3*<tu9K+82@VjfZrx`!lw;d#mFH7L?@o9;*mD$4+>eUw}ia-'
        'B*F<%89j5!ct{f9BF#^2<NGX7vb!RqGDqVA(Iy?BE+WcYy=SV^P~+vMhLhRuGWQ^#5r%X5L*t#C#4lBK$G9}_8=P'
        'hCR7L<S4|HD+rTVU2wNgXPG*QN6TkxyZtPnvYdJD5>rq!)~g*MaS7?I(p?Kp1NNP;y8yTnM@4~Q3k~OITc}^ukzS'
        '26r1K~N<=NueBrOPQHWNg!%z8*+FI^-p+W@tlBUQJMQ)qMpU#kin-'
        ')4epmYrQOG#d8D}}eT!|8UpWm<l;;iKp$UCDSy>6k>3?+-%@`N2nwSlFhq?2XVq)px0ks-'
        '!0W^WW@XMi$B_5T;)Q=$+IP-'
        'H=HcEXhFNBA{d;x>L34tmNARnTXl$9<_iWQS_#X`cnxa6t$f;I=BuYzREGjI&lFypeqM@5bLwWJXR+-'
        'y@bU?2|B9)S$SEGAIUU|h2m=K0RI+4?u6GORS?|Et|P4YR>q_Rx-NE4zKK;NlnP>xiDwFWlzHt*MthpjMN&+GY~`'
        'bX<|pCG8W<u~A>FwoQ`KW0LuPfQX(vA*`E(h7bwqbJ<DE$|i3mm5N@UYE-'
        '!mjFENH5WcIC0j5&X7FRpISO>^B%?$;mV?(G(x>dnBz@TwK+-nfdoK?fW%;7hcDX-vxGxPX@Faz)dD-'
        '+(u{ogIH+S9WR$)JjB41<7^^QWyAn_fS1^Xcm+g6ODK)h4yTw*k{K?%!-_OTB83-'
        'XpvEx7>x`+q&ykr%<hW$CD0Kh&Vk#bW614;4qQsB%K1mJp(pA@RF0w@O_1a~`wYZsQnlxSL6-'
        'tw8MqpiaQ<_Fm*74(oL_tsh^4eY^$I6Wy_LSfjZtE?slE7U#okWn~rDcc^TwH69m?4<W7XJ~ZU_cr2^;NK!6+1Fk'
        'RPkRH=pDH(tZTIkg7{jzEGo6n4;cOeYX%cwy1GO*{6Lc0(E<t0t|)b#LglliRgGkE9MC<)Xls03ZNU*(V6i%KuaQ'
        '@Jfr}xSlw}4DPV~N&?$WEnIYd3$>Yg_Oci4v^7W|5z=kdiDfphs}iFsN`PQrWzWH%_E$znqKmGV=k4=j6t@;i_Zz'
        '$<c2ls_yRm_C(Dipl3(`k0)Zd4|>E3TN6D@s^rOg`!Eoppo9?owL4t7j6Fmqgo_R1QHqyvX*LWT=6vtuDmIBDWSX'
        'WiPv3~my+jCFa?dav{_1cAXj)FPvr9~TAnBafR-twBg<7M*HP@J6gbW=Ih1UQnj%0^K?JAi@B`E_X<~$r4TA%vJ*'
        'r0Z)#F9pb6v8qYE3kI*u22tGjakLO-r)WR1n%qIBLh6+xY;9eo|CppB+P#az-icuh4E<;bLNCcrswC);CHloba|I'
        'S*#bSS~{lDO<1AFilz^eIi8eZ9y>AYxNN^DW9GNxL+V?3A>c^iwTeU%CadWRlMlf+7mbx{eN;QpKZxhfgvb|*b1z'
        'n_JwE(HyO&QX&p>6?jsMl<na{ne%_$1n=o(^fI3$BLVEQRAoMM)jPl{qKVk+pu5Z_}8Uz}A~X3$smg>5vG8ltfIm'
        'h2HcH||Hd;$696cIv<(a(CgE=v$t(NPIJ;=!~J=3*hsuXOX_WGQJkVAdl(2bP$J#k=~WrfY9!M0onM#4#s77)FB>'
        'o8AzGr(ozgAB<X1MwDg1%#6u%l<+g;+EsNa+Yphh3!UOz8QTb#vXC?*FmwI|wbl|1AX|udGkpOLOBG;<E<t9&nux'
        '9eDpwda<v*Dv1OcAch!5(h#QK{Jd5z7lJPeGUIX&kpmScFv#u*|KGlTuY*Tn%W1-'
        'F2^C4{@^`g)6q%h8V8Fc14{@D3Eub(S+qWGO3Hgz>yKGfdlh=j}O{MEoQ7GQK#PSUj1#+hyM|tWbTV?jowuWqY_F'
        'SFRd@{*t+tJ4p6RNUSa$$*<C)t@~Gz~dM8E`gL4B{Jp8cQlO-'
        '8>Ns>#_O!*0%5fIQ3WUQ@7>)xgYyV3A$Q6QPnsF052-HC@JJq#Z{F1Y6n3Br+2b{8n6oK9U?r8v;tUd-'
        'b0wwRyzEn`$W2)$(*a9&W440KLP%EinN+1!TJ(2v&7E6p=Sd8iIE=QL|6sMXcg<XCzudcIWVn0_Mecv?=bX&SbjQ'
        'O**#Zk}nXUthghifPetdt*?IvrAv+^2g<IZH8%VJQ8oGR1Io<N?kvjE^ohChQEgQn9dERyHeJA6GYd))?N1&6yK5'
        '8<nFca%B04nugpx6*UH<niuAQ6>8OP1PnQE++^yN*tSf$<Icr#?puvzTU<aHrg^^FiS}Sv;F>#xE?zwpWrOWDFrD'
        '-$mJLI-^qawD?B;dsxJTKp{e-'
        'p~{{K{0CT{^+Dr!MKHu=dfY;5D(sGggY(x_e`GcnT!NM2TC9g*HwL%&qp(ddXaZtkt${?V}=XrrBOYopYt*L@6DW'
        ';!bXVY&+LOwl^mI`G)H=8&n0_jz_O43Apq6s)1BajS?qjk*lWG6X@=FSpLP7+f590Y99rWF?uib#A<c2UXc&CVNB'
        'LC-2_7PShs6m?~+ZJ7}$8omJ%8sSjQv9C)CSoGIx54!Um~3KgrlspdTe3^-'
        'p)#d8jL@QTH^tzLH(Go8}o6Y_(P{RGceo9d%yj=Va-Sh8FJra6HL}ACzCLPB;0AHewT|h`+tiQITPLPk<0c68p-'
        'DD)eZB`0aSU9=*z=udhrTOp#1K&=!k-bkDMrLfp7VwCAa8k-'
        '|V2ucTv433bZxlF~z}SEI=CY)25vq5(D<2>Y~~d7IycR=L`m90@+!lE{|>X}#MuUuY$iev-RNAWIL(G6)0{^DJ2a'
        '`z8CEr|k<y**0rv@s7Ii8dAa@E+T$Cz;C@})Qz?d#ow3oH*_R#<>{k*;aWTz%DBk{b5_IQIxLll#EkT(pA?66XZ;'
        'X;cRX17br8dAK5VayJ$y{;YP7G~K;dw<H=RSr1Ob~r*&91N3*4HtIxk=U^!(-XSMRHG>il|!@gIHuA-'
        'RNRJaawg01{eq_ABR=M~_w}?KxT-<%^-f1n|g<@4EH-kICmFlTu7s3V9RgfbR5~8Qx)lMmTJbmTcf6JxfmVDLo>j'
        '9|yRULbnqw-N&9Ir>}76upJ75m#<6l=Q1{-'
        '8_6+@%{mletjHxsVo{vPlK#TLk;?;(B`z%yKeBW_)<l!I>Djh0VpYYHz(4E|vU2?AuY8v*{cs0fu3vT{`0w(t?kN'
        'r>=NW~ejfUjchocy;FW5R%|1-'
        '~pL|jaV{(&<hQ4}+wethZ~2*)LC7WhoLFEIv91flNST^IT6?{Tp3E%jy<{r!LcFR)|VO3o_6`jJ)xj>IK%qn0ci`'
        'I%I>zF=r|nxyG?`#&<YT1ET%Pi<{5DMF%STJ5a-'
        '5FKX~Ghk?aWCbbO>08Cx3Fvw<Y=~Y5iYNI=Y{%z{LYciG(46udR78WC_A;%4-'
        '~O_yCEsoQX2w@v1zobH9~XXU8H$$Inn!mvR83^{s<CHs`#-'
        '}>E`QrIS)c4cgn{lx2loDR$ZI%>vjPv&{O1lF1HK%o)A9Q}pUgAsbll`veBW^t`%OlfQHq#PA82-@Xy-'
        '+lVY)8r6f|vmM0a)6JnZaQR_Zq-nEwOm$Y=<|U~1e&3l>eypKX67A0bE8PH6jNo^_OMw4ckXQT<9Kuc0<^Rfkq@q'
        'x)}R{@}<2>>p$v8?lk9>z(U|{k_VScZllTiuLn*6pK61Wo;{c!LwO2X5;_pxMd7i28KS%i&PDHp39YKy$d5I7T^1'
        'FNa1<`xJmxRgRy&x;r1BISq66NEjDY)`4iys&`Qk6iBig^X8(DChtLV;@9S^DN!GH~cVA5D`g-'
        'XeF%~i;sTq#)T>U9<ym!yVu?odfJsMoyuOpJ^G;4ZS&K?1b_;lie1zDa6BL}bClU646{;Em5D*n<hs*7~qnhrJ$k'
        ';wG09X;HWtntk^Yid5&i`>_wg=mm?Dxa$d(RTZqxcdz4>>loG^OWFC^-'
        'nM0sZoaqVYgj2X)8r(7=l!6*z3r4`7{@gp}L1bkzFiJ99_rCed7la?UQ(GRY|>$<j!{ZQQ?qmR!xF03Lm|3<<1fg'
        'F8<m?#S^n}i7TWCR{Y=p^}oWJ66=^WSu7r7w66HHvXV%uSBk3)S<GC>6DFybh5w>7bNw_khy4;2$}rOE4eg-'
        'Dd-)PAc;SZX742Zd<@ZH?_D`VR`g4AojnaLof7&{(Z*74gC)0XC)4CE42J+f_19`X8ZwDUlMtYPg&Amk6up-qm<y'
        'aQ?`(2swUEEYzcc{|A35pv7X0QOV>Ba^eblM1S>J?raFCE3g^&SYSJH~&&E|%ULz~oil9B<`?r|hI+6+IPyNB8dj'
        'o|et`uw>XX!7*hu5vvRjwH5CX?~8d9g!Z057PG88Y<Ad~WC>;03j+R8PGkjSInN=`s;C;aSjCtTCu6Q0^|ozBnd3'
        '!?`G3o<KBxcb+4EXA4iS-AqtrQ!L&2CL{3q^278^P9AZmgbWcA+AFE18zYK2<vw1a@Q`Wz7bx*nh%3((H>0o}6z-'
        'TMeY_bfp7t_$cmnU2Va%fLNh-_`)V69j5vn(>N^L4H0S_agai4dku%ia)7aC(IcF#AUmlwxf=JwbGq8&}7-'
        'IR62XQ4sU1=y{5HYk;el2aUnFSHx#wvi)$8Ehf6P9uH#m#D(KLzPQ(t%^0n>oi>~T$O;zsK`F>da2}P!Dhu@HU98'
        '{R+)7WHv5FfC2@z(}EBg#A=8=@2})452)X8CGf7dPw0Xk*8j=O-'
        'tVR9kU6k*K$)FlpDgfjBp{%Ixr%1!=Ik(UBT^(RLs%0EVUjbhX{en_d<uz`kQL&h{FZ#`x6`XfK(!y0EG%8ABMw!'
        'eLohwx>I%kSy-v?2*d1&S(Qwg_XtwQT4EeWdsy{L?J?lqZVwFq0^d^G~Ap#Yz!NSb_W(lhX-'
        '~ao>J+!>u}?iuO~YGLKe2_AS6A9IH2aHQk7Aiq>n<XCx5R|TQw@{RM!3cq{~b}!@LlWwC27lCVTEFZD=sbPng@qf'
        'VIU84|R%Eg_8M_bigP%E<qKWr;&E)Q_jk1ftszxMCgnIRevDMlaq8HnldB;*D5z7_s;Anj2CDl&5;5{=JR9p{Bo9'
        ';i$Y?9Cgs2Xpa0iZ|M%5saW@c&%K-'
        'jwt3Mmg8B%K;KkAVIu9K*2<E=s25F2FH5hAlaz*d}d%ng}!<y@hJTltIlDyY=J58}6q+>uhlZJE)rYO_rFs=6an?'
        'D{{EH@ssew{F+o+5?NM2bfhrw*!^ZPnlPkhtgGDtyABpuoLy$E)1QHDoW-2Va_ZyPXb1%D-'
        'A3ct!TS_XsMvJ)iGkyvb7$GWMq`l^g0fK(FIIUl%I*mrH|7wnz+&Eg#Pxz$N$KVfq#yV2%rsahJGNzBVXO^lqSRH'
        'wVV@gc+cUiocBG_S(51u;|=_cDY9q@2A%IU16FUL)thI{#%V|TX=p5@!qo0L+4@)-nE5Fg)VcmL&ZZ-'
        'M>Y#tW0%$EgM&fvlJ^9Sro$vZx`<I4cXl<`4AV)~bbQ9h{Woh7AgKI;9AoMDIX00>2&jBqyf_A6_OXay%4;(_Ui;'
        '!CR$&VY(6`^zLKoqP)$2E}qMCXmb#J4xn$Uiyh(6;N|yjwOWc0Id}uGhr=6VTQ^vb{6WIUIjn)A|fkjkq+&Q{a4&'
        'Pf8v+@AeR8t5D0YYMWLf;6&~>>)*=};B}6nQI)4Qe=u(TfDpK^YT%)0_1b*%O%yowIjcm8SKJuM_oB6yT8u4bD6)'
        '!_f-B#Ef?NjI9XAAo9U(*-495jRrIVk4W-'
        '$HrS`HAO$a{g(b$l7O1<_Swe+5y!xub%pPnq^UyLSR`(Xhxs{SpDsBIn7b?g<U<)h!FDxcR!2halOfH2aWcl42JR'
        'd*U_6HI<fuXPWqxu5*nWdc0bjHb6@_#b?8m)+Kw@-'
        '$j?~97F?`&m4;P&0^5($3*u+_#lZVbu<V$DD!*C{8*32car{gto@j8N4H{k0Q|Z!)PMTVi$rGbgnkeD9pT<?{`6l'
        '&kiC5u?bP<>-ecR#V9f=#wLEKYu7yb1GeQMVZ~OEo&Xc%uGu%oixu=V>#f09fh)(FFA&NG+sHPT!%g`-'
        '#eUqhsWsR>>&=oX3OrgFk)t5#$$(m%uM?ko2=7sPFDTPNpSm1bRNA9jfANmDfv5-FcSJo(<-'
        'ioZV)yr5>q7YeVfe+YYd@^WtPnhG|+L=Y>kXRSC?}*6`!-'
        '*%OY$<by?$WiNVSxz>ADqD1(zcTw;a>9te1>x<YojWzj#f^ZG3(0F63-ub&xl>Jia&^-Yp$hk2QR#w5i_W-'
        'M2Sd$u^u+JH;6lbH4U&_<>glV#+P!~>uy+XO42$g;ya6nYj2t)TliN@yuiL&;w7K;Qpt4m1x|OPz+Do44akh<7=6'
        'wwr1dK0vwQ)oXg?dzz06`s^BX5rh6zx20+8yGgSk~dDlJ&(YKoxJOJa#Mf_~gp7r_I>a?;QmL-'
        'g*sHrK};+ZZ7du#2f8G~9*r%p5(z{g}+k7@-V;R>UtynoQBnhz&7HrXzH(13Z$VOffKFftTY^`pHa-cy!8u5q%qD'
        '^msT2^@(s0+ZkX8)FOP6$q<zc^xrAb1m2SG;{MNni=+|nCi@J>He)#^g{6d!F)s|zA;;{ji!<o(ZHitq(-'
        'Uc@EY$!(Z=WoCI>i~RSMugp$;t9DpYJxay#+ICdr1X_FOS@)H^`%ACe5$~<M;5DA)j5-'
        '%wp?sLsa#a+Ub@S?f}~!=q?Wr7?{I#_oR-'
        '6(!&#`rz9MeR%5rPbn6%~3wqWTzVPf9C&WKkfxRayK4L0%_R(DEmCo&HAX$rip;hhD(7qk^R+bgzNU$SH_9>rup|'
        'oR?S4|!=Y(u}PF&dQn27k@jRJco_@%KZoJ(|P-'
        'G;2M)VRD~qhHt*(qRRAn$y3o*x^7$QmOS!EqSK4<?7`>?JcyWVUIaPYemG$#5*6f0$Z_Ub@7lQ`Hk={kdo4C%>{P'
        'pA9`A?MCp21T4G(BSj5qNtCV@_hA6^PAg%T~6qqtdROET;%Y_1#GZj3jXQOi2Mpww)~p(9z%%B(uA6=^vG+9DGl5'
        'oGMgxdwI@vHsKP(H<5~p@@g8L5toya^5IpFUI)}$Lh8apJi>rNx(vK=UIiotU1d{r_Ad)JX^P70zLD|&#;%FM*jS'
        'g-qYciO0r~74$)Xe)Jw6}U^<z2CswK?<+=s(k!%&c+TW+c?-'
        '?9EVGlab5>#DWIF!TYoU#>2dB`wQg##~nW2lmdu&{4n^$D{QDtRypUaYA~u&Jtj;~GCxNfNzDfuq)Op%NJ~n7}!p'
        'RSj6Vzu}A)L)p+DuW&v&PsKb9bY&;mm%QO_&=9Y=twBjTP^eIHjQPZ@`DGwAe+-'
        'h*c|r~#_8q61cT?WBQ<gg;envKej~KV*Z6cC>$_65Zt&CilgSuzM?f1yd+OB)#CYY~>d<uFg>e!-'
        '(udnnHF{yGZY%e7I*SRnmpA6$~a%2hr^U{<4#>K>_j+nB5Ykw8aKuK0mV8}2lEjKA^c15A-'
        'CM*h0)5)ld$sUwU&>w8!5XR&k$s;}AEE2$Qu<GAoqzWg0*eu|5P^97-'
        '&Y>oW0JAumvfIO5W}q8(qFZg103y(iYsR6Ld~*6|@4%~qfBzq#+U`lshmvko5ao&GcO(NZ*w*AlT^xOk_Xmm-'
        'I`JKaJ(8;4$BUu^n?<epKGMECjHj^1K-'
        'FNxN3mi1_8i&FzA<b*K|b{OnXD(aI?(CI>i8W3?F+g9NV%r&?fl*Y8nyT_?eG7`e=%phcHGh1q(=cpTd}c3&;I?t'
        'v%!ZMc{C{hd4aJoXmYHl>N=<vo7cl-xR%)oLd6ROP-UG73*#)B3|N!($T#iA8brg6*k~q}Kv_EyR~W1tMHBF~(&j'
        'dIW3#WsxxltBb;U!A<%}Nx*zWKYT>%nkov(V~X=R~qRR@N@5$M`Qjcbrb+68FM)^$L`A+QW;J9IVc`e;gnr-'
        'I83<Ko##29VE*lY~{EZ*8biR;m_cI9rr(QcsiNsW74ap~SQp8NSHa9Scvw87U}O7p+}sfm?VlvUf#<I-'
        'F#n_Kr;c7PchN1V)`0i=eRB5wl)o^HaHrmAg@&L~{u{9CVE#_~*PM#A8d=00Ay$`wUZ6^kOH|tQ`F$`v3>N(>xzV'
        'Y7;|rvnkRSpISmsP29uI@WEditP;<RSikWR2TpnTW}#<<kwIM9l!tG@uh1ox6N~k>Q5aS~c;DrwJ7i%0EPr1MuAs'
        'buwl0csO((Z%IuTyGrmOY&0Hfa@1$tCREn%w*^`|Y-'
        '12<bEBim!!Tz%b(NNtVNaMg!vMF;wN&466Xr0Wyw$I+Mmpa0e<cCgvLBza%DTF4MXUouyr=F0qrxK&?5lQh?N&=R'
        '{2GY!@INU!&eUSsI*G%@Pi1l6sXA2h4}=^ddBx@3N{d*2Q8UGE9aM(?+ET%o<O*1JN7U7)?om4?pA!YP?G^lt0yt'
        'Cx+yT20#(clN@Z;9uFZ@Ai#7EBJgD_Uw*qT^{t%-'
        'L+uGH*a6OdOvvj<KwsQ2R}Z4@xzbrq2ryte5uN+^ZMnR$8TS}d;Q8(ynSaoRPoh&%uoB57th}R2$i<KyBGa2x_2k'
        'K8Ex<MZr^vV&IA6OnkJ)sxWFAgaP{A#XB)aRXwe-n3fLks62*7|Ov%CEA-%fUD^m1IZMj#2$z(!3%G=|b-'
        'bBcx>GCi(PsS=Jx@)XJ`xyMooDd`u;=PG3d={W$7ps{>$-otUM-Et-|Lj0q^&iS?>Xho)eXt9ZINSzFtcA$dRaM-'
        '#yH1ds65(|%O(OP=t}6@{^C5Z+$1%%~CVf3y@q777N1*82et);$r}96)f9fKD9pR<Bt4Yj?9QKN{0p>1Tp^@k7E1'
        'q&h*Fyzu01Eu5-J9q8Ic89n<7ltMqvX)`2R+KKuk?V7jd5m8E=>c^7UaE=kSbF%O_XwNA-'
        'cblWk{%(;y#|-Ts>p=xJXW9Xsw!?p7id(sh_5=pmhtcG5jZ-(qu&Yi-O@kIm%a#sO-lDjq`lo7>KCMfe5f}8@`By'
        '4}X{L;0`?}3wsi&(k8$~jjo)D!@%RJL;IRwJxD~x2ZUeQD;-'
        '3KIw+#X28gW(Ni!fcEg#+y3J~CGkxlB`XiGlgDp*>+-'
        '^z^X#IY!l@xoOQrR|i;=W_*Ofn7;}77jZ+8za8v>x(|;nNDgP_OP<H2?`o8+eB@=OHI5$-'
        'S+ZJ*_}~(Ncx9uEcnxR>c_7kp<EU6eky!z_9D9>yJr-'
        'a*WL0oolIi;PNrf*wr*GajoqN2(|wA(o`ifSx{}#B0=sxe;=A%D+;@a4frP1e)XAME9`a$gR~yq~aU-'
        '$*DU%CeX>u~irgOco%a49r(J@m186NA}iZD^?2m@VRHeA;{8N)hJt$pgWx&B1eD3~1>Lqa4o27QwximfJ~=Zz);9'
        'n~;Br^RnL6#0`r3Sep34y`5=mg7yJoGS4TLc?tr1c|}d8@M=QD7Ii(^=sNNwbdP#LcvZsZ^P1Hsu~OQLFIXmm$2k'
        'Wgon`A=V^hPu=(=h3^yk{dz)`>#ce6&yJR)3*JMRMp**YiouH%p0gqA9x>8(mrVR@&I~i_IXT8PttG0mi;3fvh%;'
        'pboJh*wBkCyoF>HKW+@J1ZRH*VY*3_$H13{WGE1&RaAELU6<8H{v*RpY}O|1bZo+r0'
    ),
    '_portable_underwriter_79773e2a0116.reporting.diagnostics': (
        'c-rkfYm?(Pa^L4y@R%>+u0}hv-nFxe<?>a|mvZGEiG6opR4SSyVKls@NSUN&XS_G}xAHx|EZvP)<3UOq@3~TyOl_'
        '?s5NI?S{X(MwrfK?pxe=G*_ExO>%iC6nq}Xm-u`PO$Y|3I=H(g(@yX3ZMlcH)xv3b1g)=eum$sYbI*L~U4-'
        '7HPhi;LT~*(G^?d*~0X$n&J!?VGkwin?z4g6dsdsIpzr-^u#xrmBR3QrxU{qu&?%eOYg($@k*NgQ(X+*4`9-'
        'v95})6P>PUie!!c5!>m9zpfumpY>t4e@u!lsrR~QU(_2YfPedq#vdOPH<ic_^+vQG+OijI{>8g5zW7YMF0QVxKcB'
        'S%>p(9vaSzl3<aBqFiv<3@c_`NX@0zarMm?TV@$ZYW{)Pzcl{Xtv*`n+jc$D@2(048tf40rOql$mr6P0DBe<`XGC'
        '?_`Z*|!AXd7bZ?d$ALB?{=T}rO3PDR^%T<xxIs)@|#lkZdoVSt@C~HST)54ak#kHh}*<A+=-%|+!xhBbaR-'
        '!8BAK+7LU_J*5GAXa`{zq3xN7L_0$Sr##)w4pjvS++F~mdG!3C!$j{95-'
        'Lx=n=z4u<?}Z!@OzNSi90aJG#33vWag*gQ<VVr1MZE#~&6As^sbJWMd4JefV#$YSzpvzo2(x5?4~ll%0mUbT!8Cb'
        'a)|*Az(Zr=0RW5H65I)u!m2xojxtz~0uU8g444h!XbNXCTsarvg4{FFSu_}^cP(^;>Rc@LC4yyz?rlGX?@=xsn2I'
        '2I-yq>R;UoE^s#8pDsw#{KL0jv+Z?y#F!xIoY3+ScM2Lv`TAHB{{<^w9EwJG#tiZ-'
        '#Sn`{ad33kmSSjQMJIHD%blm}bc<5BC{X%H-I4P^y*1$wg9D)GXjs{c@39SvFAe@jzJI9;zy@%J*U-'
        'f7eAVVLTo~Sd9)4=6$U$+%6uqbZyJJ%sVs+WL?JP%PNc0gp3IiiGA|7<PS{^ti^vRVM3%}Y@WDFOs1@7J;75eN(<'
        'yyN6G++vb%+$^<wgv&5Ej;WC5imD)_%7PVoWym+I+yb_G298vcKQu==*xi=UcuGXXX5kjbw0qD2dm1LFGY$N==`8'
        '1f3taV$)Kwrh=5-LyL}C_jN$u%NLaNzldvLDp5%3Eg;_5CauAUEVj<;#yo@zs(X+b%H4IN<-'
        '$10}rOG2hBqQt!xg!yS#()NrV*=ZJ+0%O&&EAm8d6L24N%`%nUoqZ;Gx2t+hzfw)v2g7D(j~xR4r4vJ-'
        's^Jf4$UmYgol^?b+(Gb^!gK8SWMv63Zr*k}xuo3!lub{dXxC7U3c8yG`DlyI6b>!Ji_znT38JgVQe#ZJtbT#^w+P'
        'IIlY9Lh{Hn)=DLC(w^W_=;<v8WoO}GO1-y3(*WXu(K%#ler-5=(voB*qT=4p&UR`^ZtW??u7y2kH|xDDyJlyI-'
        's0k+eZ>hWQ}<oUnMPy0l~O!U`{Jgic9QHP7%1Us})pSN^Odccnx#IwG;HOQQ%HF=%HQ5RgmQ!fX5kWwiVzV0aQy@'
        'WP4j37#<OwJENA*k+6APReUV^4{b?R-'
        'Zjl8zb$rU^?0Nb(e_B4P1%8x=p?(0RqUEW>ykK}jp#6>4shzw%<W0CEmdagrUu!*IS{$g_ytPIWei5q%mJSrr5fv'
        '1mK`G@YoJ-29-'
        'Ty1*4UOGr88?K%S;O*E@OI6EV+VOA{(xvnuL5YFt6MikSl=@eV4)$V=lo1pj8!xREXsXAe0QxK*fTcby?_Rz)<N9'
        'SAOYS%5&r~ry5jqen;v%ss+LF-;w(JP8>E(-oA#qA-m&WAYM#6xQa|E2yk~@yYJ!<v;I-'
        '|WKN|g;_}Wbx8I;~78xh91`Lr{Cqgxsmym95Nu-To3}%v`A^SDfh_8NSLznd;ZJV1;fMd4-'
        'y5**_+ao$p$H2I%4%)i~krsh2O6Q?|8gEBx$8APM<E^aTahuxm@%B;!xou^c+wRG;*2)j$ZqP)Dbr_iV@le!#SqZ'
        'g*iG(OdLjn7?xhZbSs_aW_rbAtF*`ggXatCC|U;sczGa?ZHwJ?DCveKDL`CYl$H)Y*Bi)?R^3_^M}d&}0kvRpZ^T'
        '}kE<02o-Wyqavas>r`I0UM|<+Wo|m3YQ-ms0kNj897F*7WzaEeOG$+nD_xRSp$BqZ(dVCYYr`XHC5JW^V~PR#OMw'
        'cu)$z8pwY*tpY7$r(h$7=jwp3g)SD0GroRK<gF=txy~x4bc8+=57Kg3_eVV`D2-'
        'grWn|F%CE6GBW+%0Mr@N=CUNeF4_am-Hp^Z|tSVFm^QCTHU5^Hhxts;F;670t+@s-'
        '=Qk$0Z4>L#M#2ZG=6QQy7}epUQpQj!x43)pa@rlY4zdA8+NyJN5A{jo2+(qYSB<*x%4(oj7q0!eFSc(OlDiZ}Go('
        '^xwMyL<fpdyw*KM8^Q{n4{R$uIm>@ymO%A}JbSM8HDWCJl?(D%7*@rR)Q1x7G)=#g=oU%0YZ?@|n?qODqU$a-'
        '&dI+ioRjyWtwp6-I1%8og4ZNw7X<82cfztPdR9eZKzv_T_X6A#pv$2W33jnfdT7vr%Tj?|Xl{Y%xUJD{2pD-vq&}'
        'c90fl(z`sCaH{4VL%MI~lQ@(t2W)_|@s{sQg~^h6s01>q<d9pTBgEjQrB-'
        '8UtMk^pY<!w;lW9ul<9Rq=Q!N&3SN2_V(1C3Mtj6<92x^lW!%$)!W}dJ96_bTc{j+p;dIgd$mpl5)p7=(%qaT(l='
        'eD~g#WJd1`JLnh6K8;>Es(pQ4K-'
        'HR8m!894m(}BpfI<Ay)DDm}yyQPpRo^17+C)k3pUC5To*UciE5>k}ptmbw`7t+`6egqd_S3FE~Z{%mIW<S0L>HYD'
        'Gw+_BmnYc(#QSe`rxPS3h0gx<{6T1MA3BtNWu(;s8o_+S_o!SL~=Sa~dfuz}%-'
        '@t55Lgc3oU<$Lz>R%;SD+`g_hI%5QQ!UjItq^d~u$q_<-'
        'M|5XVZWXxu&(%A;%=pAfyxVNNT4sMrKjyN<_SPvB$G=Zg7TiU-wmv~wX-OxHbWrj{pg>7Xcl&iwTx<um?E!_SJdF'
        '2G5V@B6O4!{M`z4aTqNPhVa)GjolGi`O2q-'
        'NI<2}~%n4OM{WEgh3|12R11w+L=wP$trQbvc`J81R^*)t=m}?RsMUr%xyrF2bhXu!k>b>;qT_{Zg9wKNAayJyeyt'
        '#V!`INeOdkq}%hEY>%g3VU%Jyp<dU#wlMrykswFbPuliw<Tamrd`$^=P)RNHBtgl@|m&kYm%FDA0AYqU#^`VnSrL'
        'dne3$24J~nBRLrad3n78qRFpUE2SRF?XJ)yu<ZBB!chASoAS`9DFEY+#Bv9EnP4$a=3121<PFWXg`O$;HMh5&=sU'
        'd*LDrpIO6XJF%S!~c!7(o67^$T)e$-'
        'Gr>`~g@%Do1q4mIdkPPe@6tA+Z;Rt~o^E+8$cT&*<qeFNrlBBxBYfUz|ju}HDHS|Uk<jcQ!Z4TrQ;Lz&w#IpmV6Y'
        'Ax!%C3ccyQPYGQmC!)V*<8)kKPCSz#6A&qbJ*S`&7lX6485GDIv6{ty$A`ps4k^$_^AP#Ebc{}e7F;}f>tEA;sdP'
        'Y0fU|3Ss5^k?*%yrIHE*?*d5k)3GjnxXM8VmKn9RYm>Rlz{YFiMLuj=|gN278#MGlH<HBiDiQ9fb(%&MZ<5vk2tv'
        'WZ9cI(NkXY_^>ZYp4HXE#CP1l)lSz0F4hL&CSpMwhtez%2H=Vh7IPNtpoW?o=`_blvRsV7)t7l+w1u8kjWV%YwL;'
        'yTdMD3t&-<Fe|S$SdR{;7}zx@i!A6BYEi$3`eyT=FFtQAJZXF{?Nc@S^1fI<Y8{m8-'
        ';@M`h1Lo>{aDlHuS%jsv5)0|gLP&=qeW1nE#=Yd06wO;J|9gE7;6q{g69OtNZc=)86dkv8MZUyWC19g++2X6oPyb'
        'vv&ZuMe1R;gmk7``LGujq$N=J~`+N0@4r<3f7=_hth90`bMG!aq=!Y+o6oVBuO!1`k3h5J__4Ko1Ph*O~6L}0X4F'
        '#j{8AfB|wgg5wK0f{YXw*M&!$yUXG`_2$fKmlYrv3@W6Vv69;D|!u;+*)(k+@1!lPy%EBWmt!z2-'
        '*aqB>Ilxd|cDi;<8{x-9_2|5I_4ioY#DX&fQr&~DT@J5f(gGLV$9`~;~wp01&V>PFP-'
        'yIs+~PhE*RO`1k{;P|81^#9zcKYQ9orhG_f*i4@!EdNJ{<jI6XCCTOvA731a0LQa-PVvjdCi2Khup(<|t7uDE6|^'
        'kal(0f*g$(DZ96MMp8|WF|g4N3um5;GN-'
        '(~KZF0}^U?fXaRuSB|H`3bb^buUalEv|l;*9Atf$MsVL$Wpgm`Nq>cfQB;X&y0XQgB3011-'
        '_J>WOBJ)HQVd`M3r2sM}7x?AM4@oE?%PI1bZDNm;@1{6rf;`iV-riec)KWR6Tv^b|fD5O)YBO)n(#l&5RJ)E@Mhq'
        'xZ}jOEox#h*_4=&w@Aw^D0Gpc-n~Z`&y-|tMpAv)iMHsQ)&xm**As(SKzk%UdrE~i;Mf-H_kvi>Kz)^PX!iRhMH5'
        '+WohbB1^G&BG`b&&8zH$6%cwRqFu(mf4jQ!&hgqkj~!peEBkdsdwH(vkwu_1yO=8U{_Mj-'
        '>a*or1kHku}%p@4qQBxbZVFZwJF@C^cd{l<fs4Kb~0ZUkUz<_*CsYDAI-'
        '+oFWE$X_tT_)Xh3?Ie}FyTi?#8v*}NA=b$?ZSuTMoh1o$yDJ`0jnnQ!N2+ZiadX3Sa^E1>YJ)YH$ct?&=%B{4RqZ'
        'Lc+C#f)9SDlp*e$5v!Rlk()R>k*+bcNivhNahT;=k%SYxb$Vhl6APo&rtd(Q>1ROKgogBlNVwy)LN^PHU~H*1#HO'
        '1{?m+l}~U7tt&<uc>(+ZLNCMTFTfchK<*Yu4>_4dN^>v!G4y(%Zez+Av-e0Q{Z{H#zC%|VNec6-2RLK+=#jX??-'
        '82fA}wBV|ZzLQrj9X9cgdrb#%Lgbr#K$3pkSMXydPhgGEl)Rk@!?rNapGDslR`)NGwO>Ow-'
        'Bdcbt)m2IQc1h{@R`nO=vK!M@9Zlbf!c}|m)c23zYPC$d!@HsBvc_XN-sx`Q2TIoQMlMx?r;bIv!&gl=OU??ih;('
        'l5=E&=(aO4x(-'
        '55_;B1VbJ;s#RoD10nGcpbJSpIStZyPCSLCrye<2!{H>`iz9jOb_6FRy<5Ufofz0~f|E=BFw+T1!kOSAj2FZx%VJ'
        'L^0CWP8Pe@8W<*Wdw*|9SMKFM5HLCROoY#PSrx!rXzjG1KKQEcHj6nGg&Y&=)%j1=W`lS_rZiKZJzQ;mH+`HXDhX'
        'Jr!mF`IC9U<{Ed^Wu)qBvC3VFE}aRX<!rO++3#<x0jw3UG~?@)@#$br|9H%hgQ($xLh8o-'
        'A_!wEbDd85Tp#B&Nyt!bv2v&a@!huN7DpV!BR}3qs!>D78v(eA^LtY5X&4;u?(kQv*+lyfK`29ngOk!MB8+vuH`&'
        'sS_1*v#$3=IS^SW6kd>q2EN=G_(ucdU5(x&PSeiv~18gtVr6Q4SAor_*5JYEJr#k$*JVM~5rU7-'
        'glJr(tUQmGQS0b{C={rnUQ??CO(sffK(IyPBFNda$?cyMb36i(&R8xTn+9t3xz)dA&9cp7zClo+c!8smF4nO9s^|'
        '@|;%{GX5E5t>Pmrfp!!jPYr4lMsz5^j^nml-bMyQP7)TJaT#AqKWN2hz(SNJFDQ>Tz_xT)3T*4mPm46VXL6ApbxW'
        '@IEag<x?#}E{jjq)I)vnkUF8xxdul@MVEsm$|YahgPAyp$XQW+g80IabF306Mci<A4whQk!cJsfWA9o$O3);N4L!'
        'xCJdmr-zbkSFPr|nD0an?{mPP90;yIV{Y#Z1@opC1VyJ-'
        '%1X9S2v|H(Esf6)`L@@9gj?=bZwZ^gbU*MKg^$3E@^Mmf&if&IBB1IRl@@xa~Wa050Qj!`%p2Yxy$cZ98vhn>w?M'
        'l7^(puqZ4S-9vL+TA-=S+3G6H~r}yV;1%&eB><41DT@;eWLT2F^u^E*xEfX8)EG)$)0mk+On4ARm%sAQ7t#vCWc-'
        '|+kmo;^0-a9lqUW_YmWHtQRh~U=FY@+txnj4(pfSi`&=MuU~RYk-NK?8Tf1m7<~NVjU9f(U>@<k<d58}pZ=@u;8$'
        'B|T@Q}n=(&Qd*lMM2UQ({OwKP4?rl+zeJr1ATui4s4<108|E@A%yZN<9ojFubKQKYu-'
        'RQN{3STc^iU&ei_H^A&1GoG&v)w2L~4DK?jQPQZzbX{?L5^>KLOSsn7RM#i`mHQ)Ga!4GS8Gw`hna1Zjf-cDTi!!'
        '=q41JVkVksU+NTPvvq1xyswy;I8D7X0VQ)s$I-'
        'X+k*xwjlGe51^>?jDUhZjdDvCL&SGm6xgr1rHM0^nbCQ`t0D8qh}P1OWi@>90~_4eflX17u~#1YM-IDjlw&qLXs)'
        '4KtrZd|)Myg9Y=j)9%jeR=F)INvEJ_iAsC|~(WM7nc7?=_*!LG4nPQ7KFOR+<zhNpY$&5YRN7gJZ&>m+FE`;051M'
        'qH*yupoZRles324rfHPjMm;#6^GnvS7w|0qV5ZMc140*`h>v4A?lG!z?FLtXKIeufW+z}VH4W}od&y-'
        '$HCs2^I+j+Nix{2e#s+07dE!<U=R^eU>!DqSVHQPqvib34oE%SP~mjFScEJSNihT})CVz`j}b1p28kSQBSsnrljk'
        'K+Y;)RFQ`ykXcEZy*SmVr(=^x9%54t!z9rHZj=SU9a*|}#~e2Sz{MejFqrYRemreOg7RArHCgiw_s;m1Nv9<I}{_'
        'ZVcClfrpCw$}A}%`OH#NE!o%fPA9H!cvY889Z@&De9tnB%jp1Un2naF=}&C;2b>7ALSo*#Y#Fq<(RwLl+Dc`{bsO'
        'iJCe$*@?n+yj6xcbGIg(kax0Ab9R?SLfH`se8l{*~aPL`iwbsA^{ueJk4qg&)%XVM$j})POiVWR5CKQDPJWcKW69'
        'z(IDI%e+nOp+<L2Bbw4-'
        'IJe0)^qBvfFcNjPXP#X)@Y8s%G3ZF=jBjBIiCIg`W*ReHy+Ef{XlMt#efYZx<@oQ(BTT`S^6|O%qQeI!B#2!W<r@'
        'eP&d2^Ee@W0*jiaRX0?aquA<a(aC)WnZlg0qf^Eaq9m8`8~fZP8txS%XDhsBeUsB=BB{D$$j=20(p03IC2QLpm2m'
        'bEwdh4;$GKf8THGnq{b0!|qZ7Tu&D1R_*lwctbwVKeDuoe1ezZ{m9p!(!5j5tPEQj$@JD7u=j3I0cPb`^YpmyHff'
        'n(sb@uKJ>AXG-t++&BprmZr4`1Tk?eI`@dvaM+3#ija+GRnii<JzN>;9?UqjUGbJqPDrBp5Ns}9Uaxe4uY-'
        '$qeaAw1m5=*pJD>W|6ZL6IPf7yL5~q3;xTYzVOV1nZ#`3^?#Jrle4BGJBl85V`4J1ucYmUkRzAq7Jm$F`CP+8pbc'
        '|Tp;X#i19LN2RLEq#2>Gr36+@o0?g_Rwxp#>vY!;Ck58hv`2+j7j27!k0iBjGzkEp;`?xZCa4I5AqlqufWjh%6R4'
        'f+0(|8?3`Pv*6$e(#L1yl(nJlVc(X!qJ1=%5FEwdL(W^s%8P<do`T`Hz}a|(bd6vZoAMEaoUoRQ(U*&1bmx(<&j-'
        '=UhdJfl@)JUYZqVcolxfh$ALLj^P8SY-qkSbK1H16~?6i>{#X36HBlK}cdK$`+v7SOAbNoyq2=?iqQ>0H%t#$g9S'
        '2zUs_wqVtB-}dfK%Fqspl#+)$CzDh2;?eUZGP*x_29-'
        'qd;=j=_C6nkHAr3;R%)l?!s(*SuSNEdkKU**QCgSk8t(L4)durqF?6^|J$?^+q%)zTP;b+ZE?J(E+v2`CwBz6<+F'
        'zam-lytt2i;KuV0v|R=z!PVw(hn;MAt52H*Vj^Q`zC|p5C%^&=pM`nS^TAhe~7W-'
        'FVjNVEE9}PM9a|mkqQHl@v4%3kO;c=@6vPz@q_3{waWAf7aj78@0>B4t2Qo7c-;NbK-)LB@o`Pt-'
        'l|mp=n+2_N{uQ)#ze$H2yVmKI|EnsT-'
        '|qy~0<={f;9pa_Txeqhmd?s*CZ&pm#UDI5of;g%;?E=|3!N8uxmSku|a;GxxL~<3`sM$e<ZFphsGfhUcy1C2&LHB'
        'DFN##4NuK)Qs(%r}OBB`T&GzI53))I33(L^3EvY)f_`77o#iYsKqdjzdg9N@M1^PfG0<SI&Kc>!u>hijB=zG`{6l'
        '`#mtAU!Pf`AyhYW*v$(@YmQ)~nLbuS*ot-{=q5VJ_w7mR1|0_-'
        '??pdoaPv!;B33McMZti%u0BDnFj=fOl@Hy96u)wr6UQD}IwWc~VJUnmv5m24H7mwMT!^UJai5fft_Y{62b_7gkvO'
        'Nv=hJ;A|Ci76jE|<}coIX~=u-O|C1IRvg%-'
        'v+!C_G9JE7vE$LnKF`$;`L_kh(9}7(aDC8x?1sK8?b~mkaz2(}3WA%=XC=dkeAeZ}UFQWi1=%wJubT(Ra5wN2P%&'
        'WL3>~@)elm2sj5I?2E{p!w1f*KUcw70WLa&Ck32JHeF`jREHfUfh^NoQQ#|C@viw@u?3nQHuOVoKuq~X_?ug*CHl'
        'K&LsjH!H0-;ltg4%;@Af6AwS7}sa1R{Ls#AStX%$}#1*teB^%xEtf-'
        '{qPVcqN>!DSMA_Le(^f;&>$h}7!DKd=QwOSk&Uf0vX}m6jw}L*h_1>*ai^XJIwNO~zbpSi7g}+$qshwHmrjX(_K$'
        'q7#2!CFkuQ-lb7=&y3p5^lq&h*5tdQ1mB5Bkaq%KsyR_-GEMn>@U^xto_R5$giA*~O)oR`5t~_a*iqJ5rc{uw^zF'
        '(3J~JAQctBPlc9ng(nxzA`2k6k@F>7%zVPBaiIFBl^+EGRd4Ys>&8A`SD#-'
        'uK!<?N{|M&%*A1O|PkZ38;Fs0gwePY2WZ<DqN?S<D?cN@Alyr|bwOC~Qn3ln<7nm$d?wKM4<EqTQu;DYL!s7|m!K'
        '`0v<D<{u_BbF4^#(t;INGXSDb`%N}&<BPDRr22Mx)3f-'
        '*zDz|QwUYVNn3^x!XIU0pJiM^Zk3ui=?zZLh)~BK^3eqfwNSO1}csnObImR7sinc?IA;*PL1Nx#a9F^TY`Ghm9>z'
        '(6Qd4dR6AIZ)Ge(>L(qVb1DGT%4X8{3Cn>Yr|>U{ZwrLtcMibMyej3CLl|?Pz0t_T64<tP^?NTnt7{)836loq>Uw'
        '@W{|2lOL(IH1D)Iix1qn&`hC0O~Y5}M7!pr^V(Q0@~2V@yM6_Qh0C5em*QSHm^`o>0DbPg@Ix!|Wj}g0$bv?3PS>'
        'Sb_8JMN-'
        'z!i1Q(;W|yTJ5nSOb&4Jz%o%2r!cz;**n$kp9Y^2Jbpz&(wrF#1}hE;a=mb*(<y<In7Z&B>de%sjf88mes_G6m@S'
        '_%iI~@&p7Avo*dU{9<k=~5ywrxvdzKFduLl3m>Rr_!!Psd8_lQcn%@z)a=5OO7DREBt=3YYbl63>^&AG7@k+o0M;'
        'ZXkWML#E-HJknqj_yv7<;3mJ7>HNe>C_8Jbn3Q#Qz(b@|XiS=-'
        'Vmp*3%lQ)ZUC0@+F;Ot7WJa?GoLYmxjx9SB3RuUm-uK4m<@{Jd~Y0#g3YjsT;3eE7S##(tn4_cyU&!e=V#(5TeO#'
        '*`w!W@%0)JINR#CvidM0;8==ioHhMUw*eO&-+hqO4hG6C{1<CLfMGYHTesz&>fusLJoHI;JTS#1&O--a@jVhP9ot'
        'u@duTbRdT4I`iapHI@mG3{%`W&FeMz^pValSQorF{8H~pxl_$m4C|4J03gh3je`tL*s6V&l{XB_7NSI0+~;6ILH;'
        'm!XEXbf{e*qeNDnB2N<L(o%Nrxbbu(~F_K4PeBhjPrBmy;!dgyF*pbwN`kqrmFSa*=O+7{i6!rC=YxStrJfB)e+J'
        'E^@+WEb06=1c)EwW!TG^=u+X(jV3_by9eFus_rGPn&FkKBlg9bnsTR9^DObM+Xkvkm&$nr+W#bcw{5R*|<8y#%JJ'
        '@2F9sYDzQs|+m$7v#8>KABosS9GtU$cu;BXT-'
        '_Hg|-pf}#2KrQ(>-9uru1zD{$VXM~)y)Ho)*dZy&OsOvecfEpy}g@!1iCy;c^H9PaFofCu6=Lhkkn>sg-xti0H-'
        '+cSr7&AE}%GcwwYwwmcZQ0YvOG{k5fjN4027h9}e|*Zk!0%wV)Y&Ptbw1e{NN3o9wiH%8S#F0A3{f*Y1%o8EOS?L'
        'hmuSjj1&N@VGgnVMY)RL!X?R)km4EwL5V^bvkCGu_F4c7DWr9`)ziOY7y8;oRm{eclK7buSv2O7y3HchBc|?!BOi'
        '-3*e{Jwhk{}FX!_dtl6xABaFs`NKQhlyC+1bl*R7r<)VNWdpBf_-JUdYUK&6h@&*+aW|8GnzDuS}62^)9}IFmqGe'
        '(A5SXfub(*7Aad(JsJoZ@S3rZLDlrRicB~_b$M*D@4)mI``Q(>aW-'
        'B(3_9SeY4hSigl7qGuMVw8Hs==}s@tn<P={W=2i5omJG@KNL3mS1G;$NgTgL}Y!k}BuHxZ%%B^}Ej0Iy@uK6tjfF'
        'bZDZH)6so0hhQn_ykZ%zA1}s-Ow9o0*57va?mWESUFUC@K9lxgTs-'
        '%1$c<y@?)xvITp?6$5h#QT}VHkq|_JErf{4H)`~~{ina#Z8l|6p<_BE3O3<3%Bx^mW9<)+C!SWvJ;=U*=nYH01Y2'
        'ZcNER6n%H-hb`y-'
        'OS<_MV*$V`?(f>tux*X35#BiCDFW*T69i6o4B`W7M310~egaRIgb>H<S_5#`_Su3iLe%$4GS+h=(5QGY}sHw=VX@'
        'O<B>-#X=>1snMkI{b2SoIQa!oWW7K!`-'
        'N=$HTayxx+=PE0&9(*M6Gt=s3`f35!vqrpYJqH{{Z91w~Fhf%4Jhmk6`50t4zTU?hg1`@|#D!c4;xt(SktGUBT++'
        'Ks>V8xk*RTEjCF4o*X&p6a0NY6io9fqr}*E4r`VjsDm46=IHiNrJc$Z9ePf$jT-'
        'L4Ubq>nBDD&v1=kcR;2QHEu~=yKYN&s<Z{d&t|F~CozLB09;evnFxZ+!G+efx?)eBbHf-aG64vYyf)92e)e>C?-'
        '^9wi}rD4Tw?#qvD<18u8({v+>j^BIc8LX$^p3=y@mt*g~vS%g+udEol0A9`8jNU<vFCy1Hco~JUD>6@gA*6G?CkZ'
        'L7nB>>Iw^#7mF-$Mq{Kiw!<TJnEKWr6F=LP@4-'
        ')6w_lNQm;E<LYVpf>!~ptC}cjZiqLGx4>c9{=duY?a;)MQp;}dq6~As88Fa9pb`%Wkh2GT<{+Z0#l2NQE!I1VUC_'
        '$@FU&MlNg&v-'
        '$tkD#9Mop4zb>~0$#9wby+xXOu`tGpZtQp({D`j#$qrEFTXjPQ9J@j3$uv5kM;~=%hsPBJ7(b)!}m*{!xaohi0*l'
        's=0t6Cg2pjHr$|z~rLkq3<H_^xMUmq$u*RpGHcW=ibIe=EH<B);X%7{WifE=$_XHlUF8&9_ErO~'
    ),
    '_portable_underwriter_79773e2a0116.reporting.report': (
        'c-q|>U31*F@%?@U$|tg=ICeVIv^Qa=j^nhMu@j9gCl4A8%_DI-MkK)!q+~_afA20n2!I52=cLKB^@DW;_6xg<-'
        'Ngby5PUgSbxHD;u>HQST1x(L@#Zz@X~+73?0eRb+q|yIe4r)idRkV+P_dQ+MoAi0(wflQs-'
        '$f}lg;K^);9qC6D3vKjRTKK!Rne817RJa<pvt2^12vnAWZV>>z-'
        'cYud>RoTgHc~;PGZS&=w?VOWF%|cYOsQFsj5$$oaUdtAgyuR!i06<Qe^l^C0o=e)Hi&h9CK^rrC(J1erej{4bw>{'
        'zv**{_OelKP8f2)n0%2kZgh=*lfhovur;OV^6b;RE^L`-'
        'nMMW1+&dYjWzjjknn1?IGg0VLL<G&yAEi_<Q@Izh>MrdpwzsmbIvK(kkilvL5HfLdiwpv%Xk`;ARRETtDS~8pJW;'
        'Ck*6Mi(cVw;cA(50bj3+m>V<xSiV_FrFf_GhB5k#p{uwMRKhVU(4S|1OO%v~wqGK_h{m5CH@qAC!cTWq}muhx$wa'
        'js_=x0c#{nr)il^T7E2Ihn0`Uba$o{>Xu1)Z0y9q2~|rF<q6n<<;N$IlW@?mAbrm#iL}_PhT3yav%?HP&=_UxCWr'
        'x0RCPyl23rxw!9?tnUp!DfV}rrSQe<Tgt~;(fVG83_10U3<hGV)gdC2VrME+z<M{?`P=WleEsT8_U_f27vEld^YY'
        'zR@109N^s)N^|6N^?lspK!!M>N9>ps}3Au-%j-'
        'ht2*MuV4iUNyu3#s<uUHUvDEUl2fwb(C9Ftf2b}!VQNoVb2z0e@nBEg6-I#^HsN$Pz6c&A@{-'
        'G&)^07vx1H7;GjIpKLMw=6l`#G%@f?oOZH)y6-'
        '%l@uH%bdTf_<L=Kf{x#=gyPc75Gn0tgWxCoFmA1O6@TyIkkvX0!R*lnz3O1wYX?z34|8ZN!iaFR!Z`T2}|g%6A<t'
        'wo*MoaM9;g3p?d(Uk$jxvVz@G?M7TWY3Pt6WwK{INSs4@KCrrEBM1RO69b7zfk<n(qo5=TQRt5LTe7cNK8OjR*wL'
        'N?Jv}Oi=^nBsC;>NiHDp=HX}yog*<Z=GtfkvYA=RE#ylVN7L$nh>iNh-'
        '<JI3nBAmBe(6{iG4)T_Q{eHb_>q!~evJ4#xxTVEA11e-'
        'ySp?MobPq8+uIgPJ@Kb5JJFqOLUtk*zVv>k9W?kok_VFi*@e2*%pp`=H^xH$Jbc}BiS6@U2gS@O)cIFTNn)T*Q|D'
        'zP0!kd{0bU!Mg>1hOPYsjLNpJkO5H<I%Py40?7k)c3GNUg55C#Zih+g(48%qV_v6dW`)!t2m@eQcru0j99bntB=$'
        'smp->Rv)zx7)srmau-k^AS34mlu6Bc%%*?-zXgC3u?G2la*meb@eL+<rVT9$f4!9Nhf1Xg6F@*ff1%b-(>Pm*C-'
        '^)KHie_!zAWdD@BF2>l66Hh&WhmXc#f69lNMTimtF2orl$n$sHpFEJNMWDf3EokH*6+e7CO8BtDIyWpG=Le0BZ<;'
        'M0-n?GFuD><#`dOVcevLc5J6x|%nVT$GCYzqNRC4|*MhVlIGiGAylUZ5j=u#9dqE~@2Z-'
        'NX9<VsMtA+zcXY2e0X@vZNfFA_OkF07#F3vll;vE@xlD{A?QOtCi4nq%4y#$*ec8UoI5|7EXSfw$eBn3&9)wi_V9'
        'x)*@c@!8%qqZ#;ie1YM8p+FM7N`aBbmBA30md3l>FYB(N{`vTqIHRGhZZ*;b_V*JZ)1CVK03r22p_=05Icgb9Bg9'
        'e5Hk*@=(&O)_c#4-zjVAyu>*eBKVFdooDTKQP<%+>rL*pZO28;u;4PNqs_55QQpGi!PhXKM-'
        '_aE*H}v@HQgFu=Qf>6hnTuS-3q&jN7%a<=W+;)h8905qzIj@aItS<8^Z}c_k$cL`!?O?s*1$pmi$a;jVb-'
        'mPFgv?QM-uhZQcId8qg+=g#eqE7@$GR|I9O9yKUk*@A@NjP`DFj%ggR^UY5t4s<x#<{%clBgUX`twUkC6@q>N#Di'
        'j+Ma@F1iCbX}nvfSDDtrJy45h2F|SmN8c`sq-DJw<zW86u?2&Ek-&~HK-'
        'UHO&LRHaFe%<I>mTOyp@1ciYk1;>X`F92uUAJ_ASS*t_o~RnuV*LClcNgZ5zvPkW-SEWhi7)8k`iUS{{(gyK%^{b'
        'r)K{g_5BB!XBQ`75<oxbZ@0qgl#oJ)eIFqCy>o<-6BD8j1x7bU;-LDpRtS**kM2s>e)Vw5@q>ts%0c-'
        '!pA)nyGf0H7e>PKL8}izg6%yKEa6A+_(aJQSWKnoQdkEN5hO5Z2ojO)hZ05U5Zj~;w!xGRyZj!GMy1?DvWK*Ns_*'
        '2s*L-'
        'EL?$oKcX>|&>t8GWw)&_v}X4$OT#d3PG=?k?eVaKTpe#Tln&Bz6!J90Q$VlP{ODI+64+D{f%Dzlm)`jqdqNW{!g4'
        'K?;Pl<<l8c9TV52R{qc9>%_7okKAdWat7Uh$JN_#%KJTOlFAbIFq>te;2uDcRU04ECI2mZ75Bh?0ei_GuWSK&$2s'
        'OT_1)_;8kF>UZ5(pHHf*yY{+W`7pVS*<}62HOEh6L7vP$<v`7ET#-RX2-'
        'KtNZ917oGyo}&X%=Q>eh7iXw@}^LCgN;ibEcC{@?8deee$QYUI0rXllNGeCGY%2Tf?v$daKZQT7X3SrwS2hjzh3$'
        'be`N{!XtlWHX$9?6@kw3QnI(!H@9ZUK-Kh_)4VS2C8$&j=v3g&4v`I!5Ingvv4isX9qrh45hN;Hj$3&oEV6w$Ay!'
        'F}9tAL)0wq7+<RIF^elW^8%Lpcj<A$a6cRqNO`l#Ok7_@qG%jx*;N?3OmP9cJKqc;3C7la+(E3~a;*4QH)6Noz)R'
        'I8|5|Aydb6Oa&@CZAGezbrjq#dlIv1LS)F<RUy`v*gH8>DIJ2S%8n%~MqJ`7Lnd9`<7jhJR(&WxxM;e@P>O;UGj^'
        'kTuojYB1K#L_D>q=FWlXgqh#imu3s%CS(qJ6+XMYZKy|BYO*$jKJQ>7*4mf23kzAfp><SU5pU*nh4p8@X}b11odH'
        '$P4b!O^J;t&$+mn-'
        '1(IW1gSlp5}N(>hA)rR5x<+q+|>j;*5}rKQ3aXN*|l|>?RKDN}Z6{eh($)d=)+h#dJRgrmO^tePQN9Ia&$Kk%a%Q'
        '+@eh`{e$r1eD1~O!rZ>7mky&URH=Dx6$mQXDnUUG{R<-'
        'Cn$Wrul=q71+U=b=%Iu9d8dpr^A2V!uVQT$00FK|K&X)nwo|oz$W=fhmm4D3e%&zI|+rpR2Pv=^b5Rq~caf=IDac'
        '*^Ix=8JUWuX`~`ILT^dDOru{Wz70M?YGGg_>sThr?}Yz`c{JxNB$@#-'
        'bissQ0Oo#jZe>i1w_(DIro|*4E9HIo7cXRJoB_ne9!H=THHj;J?fdm8-'
        ';4<ib7o@E9*6Su{U;AW`4zg;2k+nY|lWZ1l)I0iJjkm00==lCB=V)}*lCS*(b(minip?;HkKBBj}Fmhh<}WIRunl'
        'c}e~G(e`vOZ~N<0i6yd=@UniwX;Tg(pki<1?+<2|FIO{V@Lbzx{(`)d&)gu&V{2EHf8Tvf3sukW{zf<c(E6~HiK^'
        'R&|pP_6EDjog1lVv6$<}*Rfv2eh|Py0Z&_PGK+=T=UQL<DeKiy%#XWh4*8KbHH}=y&Bn9JLT|tRr-'
        'K46EJ$$$~s7DLa1BHZq4RJCj>Jfu%DWV+r`bJZB!63_M7>ly#(c+aBQH=_KOUMuSs1TRJu{S7uK<<>9GjZ#YE4L!'
        'rtzy|_tBM1Vl5EbDC{s8e@*B$at}3Vsf}+Qaq>#V?jt{ICy4&YPUQ)87hy1o;eWLaJ%L}!my;{4Bu;0V*;6wtmov'
        'IUAFdILW+<Xg9^yU+%5?tP<YKn`Qz`f9PkkVt<>D~yUczNnLDP1~@5JSZcw$rnou1K-'
        '*;P04xYWbtrrVmKilkpvnE@hySeyxp~S`8L&lYOgB8SYiP9D^nJy(Ds)CyyK5WOjIOt@8O(pFcv-'
        '=wO;Bn!SDrsRNSSGA|_9X0z4<n%3b+rlt4aID4E(T%a4eZr@2;CV})p+j4msG_#fe#?zA8JMUe%pVaa$QX~qnkG!'
        '$xGI8MLq36OYUZrVWQyw8`J;GY0)&jc<n=+nSUbWTk705aftB1BqZVBV37scy_iH}?pN74m#jLSG1A>y30{UoU4!'
        'Db)INwE?A@ikhsG0`eMPWrCL*$Ha@D!jS)|B)R$lUr}(w_^AQHM-cy)24#M)?!o5H<Z2Oy>#(akzCW$En}nZxhfW'
        'FRu<=~5X!_&k8N(dmF>J>Suj=4XuN^PV_k!Lf=M0ueyxZsI9$jeVyfz2X4B251ju7D_~WD-BTtQlRunuM>pUUFRQ'
        'Uc#vgRF*A=kW7ov@E|o&TG<dyAvK_-'
        'z0dZ535`O<k7Xu2Z<#WLaL<S%$TiEc89+$Y6TdzG4FxVA&3U`K!&p0p_4<GX'
    ),
}
# fmt: on


def _new_package(name: str) -> None:
    if name in _sys.modules:
        return
    package = _types.ModuleType(name)
    package.__file__ = f"<embedded-package:{name}>"
    package.__package__ = name
    package.__path__ = []
    _sys.modules[name] = package


def _load_embedded_runtime() -> None:
    _new_package(_RUNTIME_PREFIX)
    _new_package(f"{_RUNTIME_PREFIX}.reporting")
    for name, payload in _EMBEDDED_SOURCES.items():
        if name in _sys.modules:
            continue
        module = _types.ModuleType(name)
        module.__file__ = f"<embedded:{name}>"
        module.__package__ = name.rpartition(".")[0]
        _sys.modules[name] = module
        try:
            source = _zlib.decompress(_base64.b85decode(payload)).decode("utf-8")
            exec(compile(source, module.__file__, "exec"), module.__dict__)  # noqa: S102
        except Exception:
            _sys.modules.pop(name, None)
            raise


_load_embedded_runtime()
_inputs = _sys.modules[f"{_RUNTIME_PREFIX}.reporting.inputs"]
_report = _sys.modules[f"{_RUNTIME_PREFIX}.reporting.report"]
_evidence = _sys.modules[f"{_RUNTIME_PREFIX}.reporting.evidence"]

UnderwriterReportError = _inputs.UnderwriterReportError
UnderwriterReportOptions = _inputs.UnderwriterReportOptions
UnderwriterReportResult = _inputs.UnderwriterReportResult
build_scored_model_report = _report.build_scored_model_report

CapabilityUnavailable = _evidence.CapabilityUnavailable
EvidenceFact = _evidence.EvidenceFact
EvidenceRequest = _evidence.EvidenceRequest
ExactLossEvidence = _evidence.ExactLossEvidence
FeatureImportanceEvidence = _evidence.FeatureImportanceEvidence
InteractionEvidence = _evidence.InteractionEvidence
MainEffectEvidence = _evidence.MainEffectEvidence
ModelEvidence = _evidence.ModelEvidence
SuppressionMetadata = _evidence.SuppressionMetadata

ProblemType = Literal["frequency", "severity", "burn_cost"]
ColumnOrValues = str | Sequence[float] | np.ndarray | pd.Series
ComparisonUnit = str | Sequence[Any] | np.ndarray | pd.Series
_ALLOWED_SECTIONS = {"report", "data", "columns", "predictions"}
_ALLOWED_KEYS = {
    "report": {
        "output_path",
        "title",
        "model_type",
        "tweedie_power",
        "top_k",
        "double_lift_bins",
        "curve_bins",
        "distribution_bins",
        "movement_bins",
        "comparison_bootstrap_replicates",
        "comparison_bootstrap_seed",
        "minimum_cell_size",
    },
    "data": {"path"},
    "columns": {"actual", "sample_weight", "features", "comparison_unit", "offset"},
}


def build_report(
    frame: pd.DataFrame,
    *,
    actual: ColumnOrValues,
    predictions: Mapping[str, ColumnOrValues],
    sample_weight: ColumnOrValues,
    features: Sequence[str],
    model_type: ProblemType,
    output_path: str | Path,
    offset: ColumnOrValues | None = None,
    comparison_unit: ComparisonUnit | None = None,
    evidence: Mapping[str, ModelEvidence] | None = None,
    title: str = "Pricing model review",
    tweedie_power: float | None = None,
    minimum_cell_size: int = 20,
) -> UnderwriterReportResult:
    """Build a self-contained aggregate report from already-scored predictions."""
    options = UnderwriterReportOptions(
        title=title,
        problem_type=model_type,
        tweedie_power=tweedie_power,
        minimum_cell_size=minimum_cell_size,
    )
    return build_scored_model_report(
        frame,
        actual=actual,
        predictions=predictions,
        sample_weight=sample_weight,
        features=features,
        output_path=output_path,
        evidence=evidence,
        offset=offset,
        comparison_unit=comparison_unit,
        options=options,
    )


@dataclass(frozen=True)
class PortableReportConfig:
    data_path: Path
    output_path: Path
    actual: str
    sample_weight: str
    features: tuple[str, ...]
    predictions: dict[str, str]
    options: UnderwriterReportOptions
    comparison_unit: str | None = None
    offset: str | None = None


def _required_string(table: Mapping[str, Any], key: str, label: str) -> str:
    value = table.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _config_path(
    raw_value: Any,
    *,
    label: str,
    relative_to: Path,
    suffixes: tuple[str, ...],
    suffix_message: str,
) -> Path:
    if not isinstance(raw_value, str) or not raw_value.strip():
        raise ValueError(f"{label} must be a non-empty path")
    path = Path(raw_value.strip()).expanduser()
    if not path.is_absolute():
        path = relative_to / path
    resolved = path.resolve()
    if resolved.suffix.lower() not in suffixes:
        raise ValueError(f"{label} {suffix_message}")
    return resolved


def _features(raw_value: Any) -> tuple[str, ...]:
    if (
        not isinstance(raw_value, list)
        or not raw_value
        or not all(isinstance(value, str) and value.strip() for value in raw_value)
    ):
        raise ValueError("[columns].features must be a non-empty string array")
    resolved = tuple(value.strip() for value in raw_value)
    if len(set(resolved)) != len(resolved):
        raise ValueError("[columns].features must not contain duplicates")
    return resolved


def _predictions(raw_value: Any) -> dict[str, str]:
    if not isinstance(raw_value, dict) or not raw_value:
        raise ValueError("[predictions] must be a non-empty table")
    resolved: dict[str, str] = {}
    for raw_name, raw_column in raw_value.items():
        name = str(raw_name).strip()
        if not name or not isinstance(raw_column, str) or not raw_column.strip():
            raise ValueError("[predictions] must map non-empty names to non-empty column names")
        if name in resolved:
            raise ValueError(f"[predictions] contains duplicate normalized model name: {name!r}")
        resolved[name] = raw_column.strip()
    return resolved


def _optional_number(raw_value: Any, label: str) -> float | None:
    if raw_value is None:
        return None
    if isinstance(raw_value, bool):
        raise TypeError(f"{label} must be numeric, not boolean")
    if not isinstance(raw_value, int | float):
        raise TypeError(f"{label} must be numeric")
    return float(raw_value)


def load_config(path: str | Path) -> PortableReportConfig:
    """Load a prediction-only portable report TOML file."""
    config_path = Path(path).expanduser().resolve()
    with config_path.open("rb") as handle:
        payload = tomllib.load(handle)
    unknown_sections = set(payload) - _ALLOWED_SECTIONS
    if unknown_sections:
        raise ValueError("unknown TOML sections: " + ", ".join(sorted(unknown_sections)))
    for section, allowed_keys in _ALLOWED_KEYS.items():
        section_payload = payload.get(section)
        if not isinstance(section_payload, dict):
            raise TypeError(f"TOML section [{section}] must be a table")
        unknown_keys = set(section_payload) - allowed_keys
        if unknown_keys:
            raise ValueError(f"unknown [{section}] keys: " + ", ".join(sorted(unknown_keys)))
    report = payload["report"]
    data = payload["data"]
    columns = payload["columns"]
    title = report.get("title", "Pricing model review")
    if not isinstance(title, str):
        raise TypeError("[report].title must be a string")
    title = title.strip()
    if not title:
        raise ValueError("[report].title must be non-empty")
    model_type = report.get("model_type")
    if model_type not in {"frequency", "severity", "burn_cost"}:
        raise ValueError("[report].model_type must be frequency, severity, or burn_cost")
    features = _features(columns.get("features"))
    predictions = _predictions(payload.get("predictions"))
    comparison_unit = columns.get("comparison_unit")
    if comparison_unit is not None:
        if not isinstance(comparison_unit, str) or not comparison_unit.strip():
            raise ValueError("[columns].comparison_unit must be a non-empty string")
        comparison_unit = comparison_unit.strip()
        if comparison_unit in features:
            raise ValueError("comparison_unit must not also appear in features")
    offset = columns.get("offset")
    if offset is not None:
        if not isinstance(offset, str) or not offset.strip():
            raise ValueError("[columns].offset must be a non-empty string")
        offset = offset.strip()
    options = UnderwriterReportOptions(
        title=title,
        problem_type=model_type,
        tweedie_power=_optional_number(report.get("tweedie_power"), "[report].tweedie_power"),
        top_k=report.get("top_k", 12),
        double_lift_bins=report.get("double_lift_bins", 10),
        curve_bins=report.get("curve_bins", 100),
        distribution_bins=report.get("distribution_bins", 200),
        movement_bins=report.get("movement_bins", 10),
        comparison_bootstrap_replicates=report.get(
            "comparison_bootstrap_replicates",
            200,
        ),
        comparison_bootstrap_seed=report.get("comparison_bootstrap_seed", 1729),
        minimum_cell_size=report.get("minimum_cell_size", 20),
    )
    return PortableReportConfig(
        data_path=_config_path(
            data.get("path"),
            label="[data].path",
            relative_to=config_path.parent,
            suffixes=(".csv", ".feather", ".parquet"),
            suffix_message="must end in .csv, .feather, or .parquet",
        ),
        output_path=_config_path(
            report.get("output_path"),
            label="[report].output_path",
            relative_to=config_path.parent,
            suffixes=(".html", ".htm"),
            suffix_message="must end in .html or .htm",
        ),
        actual=_required_string(columns, "actual", "[columns].actual"),
        sample_weight=_required_string(
            columns,
            "sample_weight",
            "[columns].sample_weight",
        ),
        features=features,
        predictions=predictions,
        options=options,
        comparison_unit=comparison_unit,
        offset=offset,
    )


def _read_configured_frame(config: PortableReportConfig) -> pd.DataFrame:
    required_columns = list(
        dict.fromkeys(
            [
                config.actual,
                config.sample_weight,
                *([config.comparison_unit] if config.comparison_unit else []),
                *([config.offset] if config.offset else []),
                *config.features,
                *config.predictions.values(),
            ]
        )
    )
    if not config.data_path.is_file():
        raise FileNotFoundError(f"configured input file does not exist: {config.data_path}")
    suffix = config.data_path.suffix.lower()
    if suffix == ".parquet":
        return pd.read_parquet(config.data_path, columns=required_columns)
    if suffix == ".feather":
        return pd.read_feather(config.data_path, columns=required_columns)
    return pd.read_csv(config.data_path, usecols=required_columns).loc[:, required_columns]


def build_report_from_config(config: PortableReportConfig) -> UnderwriterReportResult:
    """Read configured scored columns and build the portable report."""
    return build_scored_model_report(
        _read_configured_frame(config),
        actual=config.actual,
        predictions=config.predictions,
        sample_weight=config.sample_weight,
        features=config.features,
        output_path=config.output_path,
        offset=config.offset,
        comparison_unit=config.comparison_unit,
        options=config.options,
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a self-contained model review from scored predictions."
    )
    parser.add_argument("--config", type=Path, required=True, help="Path to report TOML")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    result = build_report_from_config(load_config(args.config))
    print(f"Report: {result.output_path}")
    print(result.metrics.to_string(index=False))


__all__ = [
    "SOURCE_SHA256",
    "CapabilityUnavailable",
    "EvidenceFact",
    "EvidenceRequest",
    "ExactLossEvidence",
    "FeatureImportanceEvidence",
    "InteractionEvidence",
    "MainEffectEvidence",
    "ModelEvidence",
    "PortableReportConfig",
    "SuppressionMetadata",
    "UnderwriterReportError",
    "UnderwriterReportOptions",
    "UnderwriterReportResult",
    "build_report",
    "build_report_from_config",
    "build_scored_model_report",
    "load_config",
]


if __name__ == "__main__":
    main()
