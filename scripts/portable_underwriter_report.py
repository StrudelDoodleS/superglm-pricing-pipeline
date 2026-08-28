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

SOURCE_SHA256 = "9ae67b13ec77a0366455b77c7aaf7f38261bf76f22fa4045f16a5a0ef4660544"
_RUNTIME_PREFIX = "_portable_underwriter_9ae67b13ec77"
# fmt: off
_EMBEDDED_SOURCES = {
    '_portable_underwriter_9ae67b13ec77.reporting._underwriter_styles': (
        'c-'
        'pmF{ch{F75_g^!6hgVca|s1A2)H(VO!B*16FM4?fw{wqM#+pW+O`iCC5&SzQ!JB53?uPIsA}FigJ?MtQXCVk16te'
        '{>}$=udlDaVRa?is5+G_BVT^}NNT|kyyZ`<A$cW8yJw_nX_?WYDj7MJ851YLTPDa~zWw@dv+L{YtE+Fm`p4hD`Sy'
        'oD{qf^hKj0o;5P|fKsH&Fyd__oF6_tpZbk7cKLkhmzw+}#$qU~-'
        '&Zt@TLT}~CDrX?$oCjV2kmYrK5&GTfD+$qxG*s=_0>(x5@u-1E30+<707H1zaW)q{P6;+96-'
        'KF=dd%f>YaM(law)A$sjHhJ2yoVnv_z};NWTH1Hj==Iwe80ZWXitioDo3WWEu*<UOGuWod9qCO36-'
        'Gb4j<p<YZ@nt_{@r;I-'
        '!iqY_VcC(UReg&SSkxUZuyz<DuEp3^$S7FXmISSWO8E5zppp&3bbbIZfgCCn|2WYTd8k?`>NkgZa9*fuI>bHc@lf'
        'kY#;#Xa|sRZD>u6Tg<Ihijr)|ol9A4$UJdLOCWVS@v^B|+JcXqc-HPWWU-F%yI-'
        '!ZKA)1$H=8X3XJqnMnxpgmOt#fIYWPna&8n>oqz3}e?At>j{qDd^vt#_AKkpg3ADkY?pCN5a)5o2tz_X2_w!4Wud'
        'Rt}Ba+{1dbwQsuBrn+c;pKg^r#(_BIC>dDtQ^34;DM}7CH==^)AIZ|N~^MEB|MVCPbTC>RP1=EcdcobN%4&CswXC'
        'L={xk;Ru`Dp5oc%^K$4nQc-'
        '(wZpMN)>ElEV{x&SA5Zh*%r`BTBm$FFJnQGWh2teukUk8D>l^3T6sPf0^d@Cqh)uGDjE+o}XIE5LSB!pr&y;jRzi'
        '<sMeH(jM+gsZyh@MXW^YWQ{?AiezG8UY|)*6+AN%O8TT<qMg%7+qv%~tRdI;N3{if8-'
        '8tj&sWIa__h<2SP8t@qruQst;IKt<w?G_R?!sUcCc*CvV37J11F^00#N#Ak{(5a{FYT4QN#_FJ&+2*inrjT@ocrS'
        ')V`7M5k2vS!{bveluwn$^NHWJbjtzp&tF`}*WbI}N-'
        'I{!7JLTqBk^n`mrB*@B~g{<4Qu5}soU@NJj+=5J&4nVSBWX+H~fGpiI&QDX5gcMb^wp^#JXxAJAqV0u!5rE9_#=`'
        'NJoM;7TE0;;~cR)2D?o{!E0PGrA2zHqL)M@Sz60qT4JJB$E9I=OU0DTWSE~@{Pa3Bad4x@h8?XtUsE_cagLIkqXH'
        'r-'
        '7~K#sUK4~H_4JmtC&o%EjJ6f{%i%)6nZs~r5Db4s=dH>nEZA!WnR|N&vD<)Obl!MshDTgXNo)X#ba1zji{Ur{Yz$'
        '<+yvD!_m|OlID~2vWfDb9MTyce*nXn%)I)-vCt1q1BKz?-'
        '6npww^b15by)Pt570*U?Wb}qdcS@b>D4uPdcXS8v25@<^N>0r2PThLd?Yt13)p4Te0&Et@s$cInO0r&U!`q4K7zi'
        'lNB>_rMdUEk)VgfkCljLX3qIAGxMeRfm3w^dbuaw9xNZf}x{7Q3q@^yi!xg@Q-'
        '?gvIP5fG(r~^wcj=hMpcFe<|8U3h#aKV}(HFe`AiH-D%tGDKrHdbwiljF^ol&;~z1iw!HxWg<wydogztu{f-'
        'S*<SGp*p$K^B_K~+y;45hjQy+$LMl++V=+%-'
        'w<S!EKz%J9qqcbj8s)PmKI37y35PP4}<d98X0uV=P;FD%{qLhOB^(83xL18P_)o6uYZL@}FOf~=-U|o2X8-'
        'h6SM?&imY^53eO+vPi4CrW3d9lkYcMdGSD%&_Gx+t-'
        'N=U_+Eju?}~fg}3r<TAhyVBK3j#L@we0ay>=wrUJt<purr_;b9182GYf&kNoyk2oH{RL@Z^=z+<2l|upfQ6A`oC8'
        'D-$+d?s`z8q{iNF%CkqUVlaz-`F6?Te~tbg0jLH>7<dYO8wV`h_C(t_J;e#@I5%X-'
        'j2wE17dpPFf#2PC(u{?&KD#kk1Z~-'
        '(ZE>%??+YEL3FNsnE0zg=f4_GPy<8auD4$=I2NmtU(a28EtQqDJm4Wyv5N)E+&&M{8qZgb`A*^RZcXm$H1-'
        'A*01ZhCIO}(y1WFtEvoc!G&d8+3>uDQM(%RvY`zK|Bqu;4M`@rkPU85Ns&Q!fe1e9Sy-'
        ';XrzLFqciN_bTZy0UnBN)1U?#E@9C7=5y#?7SHnpPxMzUJ|;kgcJAraNj-Is9sNV6EV3gTpgjqV)raJ`lS{@7^yr'
        '_NU82Ynb}{>N7lRQPJQ?BbS83&2IAJ<*-'
        'OtTa~XusBW1XsiHao6A30KEH*lL3gl~Bf7n{g&DhJZoAD>Wf8i8~L)MmSJK?IWl3^L_pq{0Vs8qOblQLGc^iAG4^'
        '!M;VV9kLap-'
        '<ZDo@jAYNkb_O(o1gX?BxhtX<G%lpOL84Nl&KQaR+hoS124pu7D2Ufpu`c_g<l+MZv0(iC47donBua708I1hwHoE'
        'd0htfi3dyz1Sa2F=mPF@bzh43==Kow$^iyjd+IX8Ps(2F;!Rk!ntF9uMYexHqbjSByuS`F-'
        'Y;CKYylRgRM5}p!o&gsGr{i02L-JgCTlzSo9y-RsR-DqjvzqJ&nydOtHD9-'
        'zE{7dWNrn%Ru%Zgn%*iMWVbIB3N?(m0s?)vJf(&C0#b007o2*ITHFqBOUdThP0mFl2Mt9wl*#@UPO-TxSgwbVhbm'
        ')WwA}&Rpa~8HOkjmD;XNkVLoTf8gz@0yZoC;18t`7tL;T7q${1&xf?9fYxlncrJ>@h|7bk4;0!UwjL8r@FK$b|BF'
        'T*A)+_~ZT&{pyE5jev-'
        '!VX^BuE9yB8`#cX1>Is23FRq&?Z|w^XOH}zbd80PeR%ohRWbLmJ5Dl}Ef>o;jOs);*5v**iAmqCPTrwE7)$Nu#-'
        'pydnW?>4Z?6pzys&AX@tV^#nKH<GEwG~Cb;ISf{Imxvt5GGcSF_D=Yiu^A4bE6gc>!6N3T0O3T4QK;YYTm)>0EEn'
        'Ehrj5PO@9oU3skoNE@chOxOSY_kXV6(lz-aeOJ|Z8{@lKU@#4p*&zO6`3K#@Su_YTi1gzHL4S(mbrXhYC%3tC`Hc'
        'LQm<tyKW(`p0rUy!^1ZUGznHDFX2F35{$*z86H;{A+QeT8rbn!-'
        '|Z|~iReal?!O`twt%VeEC=g8vC8Q$N8FtMt&T+Y}hk={6*=D2N9JOo6&-^=r`M2E_y%cu{YMpr%b4UlJqk>F)-'
        '9}Mz+k;#}=y1R3$6dYNp1}1?HY7EnYh=%ICkpd~ZMg@E7p(zxzcA&`_x(PHjXzq8)INg;M^bu(jnxZ+Q7T5OHta)'
        '@tuNbz|-AYdO{fAFflwi}QQ?7mV*jj(8;sBsvP(|LPd6FdRw%=TL6l}-J%o>-'
        'BXX%R`yI8*LvGb)jraBMCpwg|qD~oqRhYM-aQ3dcUo-dZmgEwh<e@WbdOWa+rU)Idp>iqo%$F<Xmw&}k2Y`o5Y=w'
        'MA^Sbwtm@)vK5(Q(F`gVEfP^+UkUib>$oDWlDvecG+lNP%GYJw~GzUwC8Lnv2>lcX#b%m$>g@$GuI#)q{s=rafch'
        'n;MH)!iq`wPbU(|DsD3I=ZydNcZB-FbL_S~klmNV>`qMHhyY)q$uSxUXjYXT{cUMSSAg#gtyP;FT4<x398qWyZWz'
        'T^kAg!IOf^po+ptKcu~(aW9>*8V+sAfdS`Xjk%U7BF{-'
        'Vim*30>Pm4AY<@io&A*?PS1`1Mu}EB2LdKMkJdZPCxcIxt`R^R%QRbUp7X4sEEW>u<Pxa;KObAgk{qCp8JkN|LY$'
        'q_Zt;7$$<zdkv3K(^0$E)?=46;aSm8d_87X9Kd1@dXLKEfeD_<7pRT}6-'
        'a0v0^_T3Fs}u;LsZipB)TKi6zx&4P)B$*qi2q<QbBF=2n)=c9p*J<|NRUpgT4_lYn6;hoP^i^#6&e%Zvb-mgeG8y'
        'p+X?HOR|(385^j#QJkShU~Va8Qg#CYRl@Wh4vlT+8j=2RU{LpwTf2Zv@ZHOa^jGhC$aw*GrBSWlMcP9>=Yr-'
        '`ZWRpCskPc%lU<5cSpAaOv7GRpvLvkq%b94fzC5NZiw>0;3gKrZ_SoCd@D(9VDypK0wro$IIJ&>Qcd*Wrt7yp&RM'
        'pi-LDdoQERN@g=E7Qh<6r%j0(7F52aDy)68u#=qulr}1pWtx@WPq'
    ),
    '_portable_underwriter_9ae67b13ec77.reporting.inputs': (
        'c-'
        'oy>ZExea5&o`U!P6(H^%|R?cWvEhap`Vy4Z1HuHhVoF2n1Q89bWZTQF7LsroX*2LsAm;V(0E~z}n<+_;C2laAq9W'
        'b+7WWsaag)brr?6WKo{5U6hI>szs5rO;NFEyRG;(syVB8SyZ*iw@cS`9cNP&84JTrQ#Tb4Lnbnu1{HZx({ib0;v!'
        '9XOe4!^9UH+9QCWhr1^dkZ)9^gzN*cC~;xv+yOC#A1DTy+wA5yV4v)AxdP1Ji-XvWX;{erz0HLs%7ar9u`WaXYkl'
        'I5itD&f#D0RNYX<6Kw8I_25zzT_-0%kSJxr9kf81#>0e@k-'
        'S6dEHcb7#Fg3@13_r+GP2s>gOnJ0DZt@U9tbR=eygaMO5FzNM0^s&#H>{@TE+apFtg$us$oJO2{Jrl8bu09!_*%w'
        'e#Wpm+-^+)yMGS^77*CZTQp8)w}Te)78h@&!Fr3lT(uT{N?8I{Ov_}{>#<pZuaDd*Nzij-+cP}`-'
        '>0ZyNk>7FYj+*`d=3}D|1tK0B6DUAp-W~F!--'
        '$nH4)(zFw%&)<i3I+75QMLecLR&a>k<bg}G9p783iLUZ2`%`U2{sJxpduSLe`i@#D@T=ymtk|*r(f#)n@b=AoF5t'
        'cmcHAPuWBxGyO%Bo13m?w&|&W|mXJYdW>o(H#8!~HoBpGsnFyYV|A%M{FxZesib{Um-UL<~2M{!-'
        '+|Q`DZgv=(*BS9F~LbFV8ABTus;;VH=O1b=i%u2kd;fyf|kQ?X|~rSp;VMDVaI9(lD=*8+U_i2Dchj}j}&@ZT#Ya'
        '^w?G0LPM|0mWe|Hg&iba6U8rnx^BX+VR1Jnn?s4L981*v?Xw=1+rqtGoDYXt#}I7+5ss5Gt7(@!#9p$2$kCsf6>5'
        'N{|MJbQ3IB!48hi^h#@|W^i7IOuv!c3&!>M?uthGiCJSSprlAzyc&AETV8S;L>Pj$v2%>cudXlFbpS^lRmR1C5Zy'
        'G%prkC_(i6$#OzZDT1hU8S7Xh+FH$ZJN?L($(=>M|fWk~uH(S3E1ht1NA_SD!khU*v4YpO5TmX);^4UcO+)wHFN7'
        '-jT9{M2s{xsJJZB9Zy1wuZQ6WK|idJw<(?91sGzE9iUyR{ZO(7B(4h~feLVyI}t%NWuAp7IPs5J6=Ah;%|>;49F<'
        'vVf%+-RvS=34>5CwBS3sEX?!idxOrtw{3Ak2=9ah@wM-Inzx`)pwkh2ro>$HatV_zO+9Es;y+qo2j+=V?j3_`>CE'
        '((oS4x`Xez=}e{$x#>@3XH>0Pr|n?xkDQQ)wdi{p1Pu_upl$|mYfbS7*WXo(M~`cZ5hT>xQ`QSg^m(J!VzjDhevx'
        'YFfjS(dE*%faw$zIRA**a8}cLpHtrK*dTuW~$|)Rgfdj>c!ON2J2xgwN%4gRfp~W*HAIAnZX(fPq!wzIAF9JGJ-'
        '(jxd{Xviiwm1ZQ;^IfhC$gs(p&sj=hCQLb54n5nOng1^CicUJ?Ue&|bxRb*ELodweNp1vP_`$5EPqW_?2VmaLgCN'
        '()W~`x`?^OC-J13ruL=Y-!)8F?TFN_2m?j)FF$y^I&Wh8MzN#i#SEYT<*wFwzi=m?tr3X2sq&sfTYd;_d89-'
        '+pWkN^UFt==y8Pme}M!lE~?s)l;poOm#>HHDi&XQO4zRl^Tvy(2lqpZ3EgtZ5UayMu7184jz5)KMA^;W|1a8$p~u'
        'jqY-'
        'J)$O6mB8>Jw_jQz2brXDciL<^kGmVC1NY8gA;I^?yZOJp6uRLO4$@XaUnJi&X|Fi|DNKSzs@@ui8Kp(Ol`u+X`N!'
        '>t_iQ5|A8xCnqN&TK4zZkHsVbhHN{+b(B=b<&z5|Gt6~t#%A5guHq#Kl^eMx15s(6$kBv>ldry-'
        '05;UgE@hdQKbvCWIhNF1}r&#EcH6J-'
        'tRo9Mc5gWFEPg=pVI>8e+*>lzR4L3Kk0$LIvrAr#n=f(?(b;{vPercAk7yId~shec0=l}ZdnrX1-'
        'QNXeI)iLPz4k=%l%%T6#N)k!h6LBgU6cRa350G}|EN~`F3T`{|PqNZ|Mf(LZS9lI@+>A{u8X%L9_VhD(+_gmLQ1Y'
        '@Zn%BfKEPre`IL`oPvG=mZXu4~1fNauG||7|w8AnkBR-|h|1VHmJSlCT?~3Hoe6KI)s}fGiwQWK`;4NJ)9_!Jv-'
        '=_?fi#&UZYOgPVB;8hI{(b5Tl<aTe9_1NkNCbKCvVN`O?z4c57wwq8bQ>b-'
        'nR>?THF=^}@EL8(!;k$M{)oItf^3=k{>|N6#5RU1K#jqY`XH-'
        'A`IZZ^fAd0(@o@0GZWGH|HS_}!Go&iUG|9O%>Qjb{w{fXX`-'
        'Q;vtSR?n|5Tj=i7Y+p)y#evu~PE5$0cF3eeMEM1E7Y^LCOJakZgBF=KYO7UWwl-LZ1i_@0VwMLs^Yn~Qm81Sb9;!'
        '`jane>pDc#;9vLbBVVzFvaYlVOCOnO6`zHRz|4Ylr=IvC`Z*Pvs<&3pEqozMPGD0n^tCuvM}tGCs$C~TKtwmO8sU'
        'a7%;&}&f-H4K5Zk<is`)pn~0ZmNxiF8d?HPWbXysB1h4f;{ntx_#fDA!N@-7sf}4kto-'
        '9VCPWFsueqQiC~08bzMzHxCg6^-'
        'z)7SDzd=I)CX;M6&(((v%(1eT+sjC3$^ed0Ex9er~%qj+cR%q=Fs6S^;WO2Ee0M%{b1XoETo_*ip(QWd%|;QS7np'
        'Q?X<Rbi-'
        '2_}(GP&mx>dl`?P_}d)PPQgRbOP*&Po^ztUh#y(1CNN_sHH*zfLvF^l|SD*n4&s9J9A+<S7%#ag(e)ImRQq#b=1u'
        'LbIMI{4~l1@u!w&$F$h0=#hMTq2E*tbv+$RcqB5}f2~z}1HpM_tv}b3rhMyYd)REIf51>7`ACnN!gNZ-m5-'
        '30+%SZ+A`IQmzu*(B=I-+m2%BjP$Qm#!ufVKq-TfAXKW-'
        'K&SeKF%J7+WPA3!vDBgcTWQJGCbn%uJ|c_4_W+g&j0urnu6B<|$q*?iodW(zxxj;U>BbaRZpLuE+dZcNc%7ZorAR'
        'fXsM&!`1vHksGG6@zqXTqRSDvopW9q9v**-'
        '*T@@l}(<FS#4hb@F%~s4r##{W0ecNw`s8bu(p^1dA!n?tTu*frpk_ij7^0(n+<ZI7xXJf62q>WQVa!uEj9u|s{X+'
        'hqG6%(LOWxCBw<n|6b=(78j0FR9KtXa*I>NY41usmRjyryjV@R5q*(t7j%Ybpt6*H3wNtYN+R=U<9pbkaYh(7eSO'
        'yH&r+}1S$UO3Ti+l<kzYlCbIn@L;PZETYHcns<K_jlK{lIalIkCXcP)oIU1VA?t#zLqF`)I-'
        'afK$OGuuT8F!oSA6tQr17PEhfWIAHA1>peV+hHUKr5XpyVoq~}W{YeRE>nHhrq(0<GCes-Ifb6`?x!j3AuVMK6rJ'
        'y|9q-?fNfZNP&{7gU6i#)D-'
        'jzZR!e`8y?v!~HHdLCyL=#zD22cO6os3?~faYs7LyEqo{3IFOPRZ*%=TK6NGdhdf?*0q>;9cA#O-'
        'cWT#y+_TIdHoz{>iIFr&~v9=Wuk%lXKH^_umo1j?B*x?Ye6rp^oiYnc}jm)i3~<}(#g&><O2O~C#lllz~s`yEZa('
        '|2a`if_|E?UtRqg%'
    ),
    '_portable_underwriter_9ae67b13ec77.reporting.evidence': (
        'c-qxHYjfmAZr}AQ=t)(IOlBu*r*fA}Jg%(Qa-zC@WwpLbMK#5uW;hb#8FG%~?5<AHe-'
        'F@4pdTb9uYHxPE3by#jYgx<02+-'
        '(&t|h%)pc96chBnb)VIYxDL+=*vfh+QcRC*TRk=<2Ch0a!TW+6ii@r$O^4PR}Ro^Vm&R%SbV_&vi0!`~~U-'
        'V_NtNI?Q9-'
        '3{rPYS5GD>i+XR5gI<Z_BPss>9*b7uWkT`B>~vWzt;#PYG52^$dy?^aT4$ntFc+f7RXTP<Bb(w1;9}{iWQ_;o}i8'
        ')3`3qX0zGZ*{*F4NuKXc{i!YU96A!Pin?z4qOSnZ*_rxwDEeDjf79&u&^?weitCMT^tw16VT|+Svi$Q2`;fJf0-'
        'Jr&b%2nnX+F(i?ByP?gE8z2-J(7nu8~5j_C?*7H$dlk^1dwgvPyq<wBS_7@7m_`-3KTzRp6tp^Qr=(BMhk3H!uP-'
        'F6ixemlQy)qyBU(>MeYL{~x!SMp%F|ke}*p*?wvfUj8pd`Mcj=fBlc;=J&r}*jcXX<Ec03rDqBJ@AZrS%3r^@c$1'
        '(1_~ZG@5Ba~pzxW}4_x9q=hs(LCaQV~wA78vY&tLr4#ic3C&d$!&tX-CeqVB6rveE;(5^ZNSOxDLT-'
        '!#x=UDo|f!kitEor-<FEstd_K<JWUvpF43$bZ{>-'
        ')x{xx!b|4>hkWkIOf2D(21C80}+O_YxY%>7dJO;c>@5TXnl5JtG?Se{U54&>tWfQT3~I1!Uo#jG;M{Q-'
        '<CyxD2}@5Bdjl=Bn$|!sx}oF63kZ#ZF17uEmHsL&$yhLHt!Bi)87hY&p*SbS54Pl!s7V8=&Fw3I%}Ix(D4boOlF_'
        'T>gKl3VL{E-XP2<R+p_Cmke9GNPOO=tH8v{tdtMtjw`*!z`%u-'
        '@;dIDRW&lZf^>^?u3|Xu|+GulXVV0YN5E#(pj55v3^H;Afq4qcbl>hGeb5R5gbpHOu%MTZC-'
        '{kM#{)v>Hy+8lYpDx~?|G?_JeEaIB*Ke@eJ)f~<azFcwBfG=@2q83k7??(^zb|)!f-'
        'MrzZx)(j)6Ks8SnmBcp}Ch`4OZ9ufK_=7&Kd*VKb!>!mA`%e!}<FVwNj5-'
        '*&wyj7`3uNYNbJRvq5U5W7RFSQdMJ~MaUKHAISCcr}uw6XGHtM#hV|Hw?Lr&rL4QMmy+>5yxJoxJ+R7MydFSg=C9'
        '8Gc>e0w=sw!l4;L@~{mt9U4;L@VI+A^83dtW*(4xHF?u;x1W1+gP_EmqUKiw7`2;d#+a4LYilSb0W4h;kJa&hcHG'
        '6<!SU!K2y@dnTd4O;wnNOcUWk0~l-NR14r5-'
        'bu_rE~Z0)!Prz2_(HS1v8>#MikA6vKde~L8W7c_438L7vEpJy7+K$&IfZplLkW}$ehd$MO7<`cKDl6QT#4Zi2>oe'
        'ZuS6hFE9T4Jpca1r3W>p&alzD_iw*{b^aP`jX#~g7jl2LYo+;i2kZOm#dB!W0rR%Vn9Jmw#q)==v$KCQ7F;TOT77'
        '6wWp*Y$ftiNGc-'
        'a8HpZld4`K~Pv<r2)P#ShT(NBkwe!w62rehIeM0!*&9E$+nUBd!KH(xo=<uDZURlZtCmQ;x?2u!ETfixyh<r{lhq'
        'Z5NA$Y=pdCv=wM%u;!{BsI$eY4h*LjRDc-'
        '}C0ciH%Kbj?z=W_x$F>0@@sOi|y0nVh5|z>u{=Po7HT2)10f6ndV4x!dfW7&tY?sMy-xLyZv)jRZQY@4IP2Rwgg;'
        '~RYMyEv^kv{^_<*e+B>k^0$#1TJ*^cFt>G7Jd*E4qh&ubXDCx*P51WpON|B>Sl@J{Hv;&1Tu*#uO3SJelhy#adxn'
        '$x)1<_M>Er3)7>fi9}Br_yI0Gl>Ke9wS?-LQ@bgrbxEwc*JWQ|UD;VD49I2T*_3Qlo(-'
        'wjhp`V?9cnm^qV^g{eJ&`?$)FYw8L!%QEE9JlB8uf~1?WcUB$>PJ#N5-'
        'G4i{U1Qb8^a54yF)E?F;d%G`3Lqw>w9j40X~1c)yTY?aQEa2cAiM=mw88RDd^g&5TI0PzBo#qomwtfvtD2%D_@XV'
        '_&elfc&Nar1K1R@=PzTn-3Z)G4@CPq*c+IPLpf>bJWU%IWM;v#YF@(R#WkVLJ^?o~V#-'
        'tKy~xL0WCPQP5wCbw)+5-e+<y*nnzmtLu|eaE{(Vg_2+6rgWM38&y{|-'
        'L%c=NR}$PfpSN%yYsy(4%Pn7{_a1Opl`X((b8VbMAaS3RxS>&a1t#?MG^YGIFVeWt(sWI<#=GOsX}r1+ZTXS_?&7'
        'a2Vh{`Pl0H4+R|s4Us>{<h>ljZf(o3^W?<HoV>8tbwrr_av33}y#yalG{m$CTe`o&`KG57qNn4<~L3%#z_l>eLxz'
        'Q=hv*g)#A<h!|wWzuhDB1%LfxQM|xZIw%ZPQLRqu!%M*C|WN!CTt4k|4_<na=z{LC=I(xdf^GwdvW|Xtz}>q&??w'
        '+Vy&_ObdZHnjXqgd*zG?Dhk>mhlb$DG0$eRmlD^csJB8UH9%8|hjog7s`^_^i)UaSZ%-'
        'TQhekIvLd(JWtbp*i6BVOM)xT=d?UK6bld7xgPOSJ;_A}Sx&D^;~Pq3KLbf!=`oVq@_E|UUef@lLawVXMjmpgRZv'
        'w_Zl)uny}8C!y;wFKE$U4O-'
        '?f{Ww+K`zjyB`h(w#HeaTp9NUIhb|>pTLRdYDFwplAzI)}0yLLZ^dGjS8o&ZJ5K0O$$XDxZ0Th8PzFnfiTG8hRZV'
        '#cc1rSu^Lux3dLjoB7Gxhw*Rdwd>Y9sUt&a{Rt=Nb_L5$^(#8=Y>J4bxu1S`5yCnc0;d*Fy37!jpPjP^<#*Syd?='
        'Of~tFS5fG!HdGKu%6}0i36bE@%n|}J&NOWa8onmZ9V%j@eMM-'
        '^sg{FvkEXY2mIH?ZoitRjdrI>|+1`|4o|g=iWx?49&4McsBmi6un(9g(C_j-'
        '@1;fJ(>PlV3(K_=%^$}B)Ae;ZF7KUYXl=WNK7HvSP@AtT8KJANEe3o7bH8y!v2vxvxoGRrXCj+Okwp=%`KJ()qO+'
        'nGCQ9o)`B{TVlk_pz<#CCQX>~{;ne#<<2leeZNwmtpo43Juyb84wkkE+uNElC55$F98v2d{cQvy2O3nc2Dq+5jf0'
        'YteG->~~85`^_1?J-!AYj6GAwE?l|7(N4<B{z=SCLi3e-e4Nr!vc%~~{YJEuG_r$Rk#SnNfR_A<5J-'
        'Hmv=KiEIBn3=Ci<IgrN5AdWXfn;^4T^g9~A_5b*gf)N5GW~`_dl0o2i|$j7o8Jyl<zCL?#4LwB;0=<nN=br}316G'
        'cLQOs8lkFSiszriwQ(!sHoPC!TCr0D(#TntZo8fAw~-'
        '%_ZFkC+6N_d1k%Xs68_cmwK1P+SQI(6B2|^Im+K`{GS<V2wbG|MR~<_WMxIw)er%5Nz$cZ+&Pj)v&;h&_!<$v+;D'
        'c23YKTG3fZuj|JRJZ7-jF0lT1t?6`!^EZ18>#!21X*)UR3Z9;Uh^AG|-'
        '3~QniR`ap!dr5>=kKQgE1>@gOm!!ZD&!OyfjlxQ~^$%mTtqK_YVBgA<Z}Rt5^!gW@VB_F%couN;mm6Pa9OV2m7$K'
        'nlo7R}e9HR4_(B`m&RAmRaMTNMw9BhLFd*Xg+!$aZz9aiUI?gqUeK>0*)_Yi<N-'
        '3Agh=G@CK};zZ|m`&6AAph#4D|%iIXDn+7TJHLXdtxpqUZ(5p6goXx8=<F>oBoJe~lX>f%&hI~K?T5-'
        'tMA~PT~vDiGsY<qUB2I@^v2~X^n_E-<7asx(t-?wQ{98*NGX)0P}!UnY4a`Dl+ToNFa4oR#!!8z)9L?9oun;-'
        '4VRoj!XYDPg50Sh?UA~HbZNc9~LL<GmX9P%}h?zO)u3P<UE8QBSTGWs2Jaa2z5SoG5UI&(kGGULvJP0&^z-'
        'pj6}uD_|P{<JM;59-'
        'jm>riE`Y>Q_JMhFOC=&d*%kn<E>RP_NP$3qC|t$R`6mdOkRC8D$VpQftQ4jQ2GAZul6l^x4ghO_~4SK%?tov@iTq'
        'nsSVzS&$Y=gF1qTbe`iPgtzBk7`Fgv%#;|@YnIqO4n^!9)<IlSiz!&#S*=KVo#Y%AgNm(n7M^6)H_BsO1W9mAtwx'
        '+r9=>*EjAOF60qMU&lk_LMN!|S*<)tZ!ZplXH}$g`V|8F6W{e^PMHq+eT_eON&=B9^qu}s)4v>T?onWI7iC7IsQT'
        '0t<?D3!m54Q;67TxKfRe|cLyDeIGgvmcB2rx?dhY*bQaq*Y3ZMt+{s(H*n(O_iAN_51jCt?ibc!{He3`5r7LsP9d'
        'hSHNU0LeH#yl*q62%>^3<#V=@B8nI}h}Fs&*`g|Xy{93<SIy4h*x%V*Gm`HKWN^=mRt`zN5DG)|b2g$8@6QuXCg&'
        '0Nop)5@H(f@Q9d|uVI7nfe4(~W+=DKZ`!)WpI5@}+Q9#BHi4*esOpUXRk$t4huC)6UY{y{2)&>TB*V0|gyrzVXLj'
        'bNgbfHMLDPOAw%AV+zqF==38Y_(>Ug^7bZ8{BE{L<i3l-8HOx^#^XFm3ddx==5zqp)(_d2F}P=D-'
        '%I9+^aWDig1Ub-'
        '`oah7Z`bGFGS?}Z$?7>(V?OKOhBo@b2E&#(JV6aKXM|dFlap&Dhy{jEfi2mjH=%3QU9vYY6AtMgFgedv(Gcz2`d#'
        'rAXr2E5vm2aDljYC;t7Z<gR+wjf&E>A@e0i@`HW5g*}FwtEfHU>OJG-udg~ye7cLoK2$ly{foNvoluA{n-'
        '>!m&P<Ws&D0gx1Dp3FOJmlDP6)}k9SxeJyt6KVy#3X5A3(cY?#Z+e|ux)E%>M_b5qjT^N*to(UYoBu!jh<o$%cj}'
        '@Hg>POJk0DEFD0>+<KbT($8p+Q$Fhh-!vH8@Gs!-'
        ')u_Z^*`y8|wNokm^K0DylVEEyM2C52~a8TbeW<M;0D9V}l_6<&P7*BUGIk?hbcjezmjS}%X@B<3WJX|-'
        'YdfVv<aF{^a(AZydM0W*rCf7nPZ|()8rfd=%ld{N(Ot;~eoc^SM%Xs^p3kCv+xF@7Uz+V~<H2hFhX-bmHqf$b50t'
        '*UpN|<$oH?{BzX9D5_1f*W6@(5M*MaFIIrYq2e$REB6<a-'
        '}AwJSZv+&Qhp;>xJN05`6bQVY4YV^)c=e*KR#$CIiCxl;dzFp$%~Vr&v{4|_*s%pw}{2!~F}Xyb?zm@v<Z{2g&|+'
        'PU)$f6BHh#9jt`3Bx@eY;3G{<6wKNGfTPa0$ofr^6AntdM^OZdL2ZU3mMz44WN7XYUIO^4<gdNhFM|MgpgBir!r('
        '7%}?)g<x~1o;Ntz!Abim)zn%G%J{d@_XEouXcc0B%?KGs11?L668<r!IaG2?c@*!rkUhiB+aFHi0w_aB@{zs&wx`'
        'nChPi7a53=96!HtFYp*tOVeG_>u+F^JejF}p<@1B2sNzhWi}Ee^vmMoZM9HZaUMB9Oe9F$VKQ$Ke3bA<v<YAh#<O'
        'x2aOi^8;3nI^Gv1j=TnN2?Qy-nDfM22up{es+sQdPVSL9YgI8LN?as^X7zDVbRrr`$2Tp4cg`|$hb_`h76$x=hob'
        'u#+gwRx7v-N*fm^odn_MI{NHbyk%Y7iM1c~~ZUc$ikRo$o1F<|xQQ<)09t`PV-TOdbEAoxK#WT4lzit&MMk91&MN'
        'yn)gh-'
        '|HVr?J**YANlladXd9v9ef~Y5;b8xF+Rt<hpz2UfqMXYQRoKJqD<t|Fkt8xGOKP*v;L)xxLvVSc(Z#td)E>lmTKe'
        'l;j>kKX9Q|^vR)t-'
        '}eJRA7EPws9~I|I|63ja}D93FWdsS@f3~(u>*A+30OnyNU?_8nmRSqrcZ+TYGqqYl_<(=mH<$S%l-'
        'sKFch_DlfJnr!O(7JEL_}l>nbpLZ%B<Rwp*0LjqSulp}Iq%h93i@Htb<QvM^&uwa#YSay*d&BBjgS>c;{$npSShF'
        '?}Z?DZ!0f8!6DCKy>#=i9SUC>$ceZT=vXA<q!}CB>rM$iY8Dd{_-'
        'MT$#MAO;$8!Ha3(~*MsMuV7+Bmq(ii|~P_&@Wk|X@L*xWtqid|{*{b;H4>%_nM2ERSp4~%EX<~MOvT3H9$+offrX'
        'O$Kq8|J~|MGMq4)g6kR`E|K#gcF;@g3QJSyWp`Ka~YR2ct%g~;El<lhJX?nvvVzR;&3C~NY_JT*yhG)EO=R+cF=z'
        'ClR{eEF2%-lF{#fMiu&L%SJ1O=C*Hc%*`#u}y1An&2cUkCp7ke}`zgLcm-'
        'i|+MrxYO6N^K51YvL@H<Qrb9a%08CiW~KB9KHm31L=80|D$Ze#3Sib}driSU2@9m@F&^zs&QmxNaSb7>Q)??#*(X'
        'yy5^-'
        'UY&t19lP`K_k3X$5{_C$a_P7<AYB?)4BJ8+i>lSOP>h$#J?k9on^=OGX#Z}E85Dr7&;lWboGeZQjx%n_YP6?bNP*'
        '$_(;pP$F;4NmiM_KIQRr2>Qps@E3zX$4Ap&=6uNUYH>0xPX%g^byZS>B2FtEI2DqjoG6~6?eh_&*FHsCWglfQBpd'
        '%&3*aHRSdPni7lyr^c?`!^0u5vd+^xaw#}ZyV$UJ~}*l7M;e`z|#LsZZ+5#$$)aB`Aq1Q;XxbF$-'
        '=N4_Nq!NL!5AywGNkr-OV>sO#-c-gWjtCQ)80Yc=}w%08_S-'
        'WezvVk2ARimp{zafy~5R*aDr7f(i*$`qZ!jYAq{J_wrvFR3IY?tgWRGxq7}vF|U7py`D(fgi-byuOtJ5*5=GmyB='
        'gMZ*v?sJ|-'
        'mIn2+S{m=7lYn82jWv%u9MPdO!aC&r5VDs(nJL{A2c2Ux4){=_>Vcg#OmW!~HTTz=}T2k$yCutkai(7L8#I>YN)L'
        '5I0G8|BS=gWN+h#623r$65kn0(3Neco4|qb|AxEpa`}*FkX5+d>>^SNA6<4J*EThQ74id1(1;g=rOudkk<S_tVg#'
        '}ajX_1S1Ty{90BFRgQ48Z^2U%`%^YOVnuDv9+VoSs0b|S9S#05sWky)x3iS2@Ocb-21-'
        '_f~j+{d&0meGD2QGZm>A3YR-'
        '=aLwt5ICliR`V(#w8FRNPKB!ebe7|G~y31aYFox&*DtWX2;Cfq8G(FXv#xi>6x}weX@}yeS61i2(Rl(C}$to7523'
        'zfeoKG<*~Ouf|1U+Q#X*ccSQL3H+A%6Sc7lC;Tz~sJ9{y{M-Y-'
        '<Z_9`wCnib~0O*6`pyzR_JVT9Qa=t!@g{qs16RW?oKk?XxQ$nPo9TaDDxD!Sy0nQ&1Ot}~GXh#+ZHvxy7^kE~9dB'
        ')=&CGMmb?jw~$+O)QdkeG{-'
        'YHpU^Uv?VcK?AC_%_l;%L7zs<a{i@ePvoR67<H+LAD5uy&dX39<12&o+PMOQoUVan>K=@8c0c7JjECnJxe9|hX3}'
        'WdVKTU|xfRR6yYzz&7of~Bp-'
        '1Wl8D=_3)X#PEsaAw@2&KqpfEjF5t4C7q7FLb!Z<utdmL}b=8U|@}n5`Sg*(^O9T&uajgF%6^QY<D=mClo0fMAPz'
        'S*&l7yGVM8sDBZ5;S;XO2oBg%fsn&+Mc8-3exoam%Z|HRV;eagQcGNY-07<<S9NeXyeqW8qL~(-'
        'WM<+Kp6_y!o2N*cYBwLXZjBmSM`XY*v)YI|q*pX!_gb9;N`J~zwjV51{kHg6CNhkGgg<w)i1#*>TbW>O{e%Sl2?v'
        '(}uwNQuy}i;_k!D)7s=uCsoBB73m+K9}voX-&BX-aKgH!#$fd6`@`T<e(v{U^6An#Pa`*O$nop-'
        'L^J>p=0>J)t0gZ&XvJ|aa&4NJ?~%4Cq&C<2N<jb5n8f~G)d2DNFSuMJP1$X|X}Wx_ob>K@V*b}z3uH&!TWG-'
        '8)!{tsvDf8bb8LmCu{?(bm|zE1Gq;7-'
        'OKppwMKbT2a$8aw|I3SGK&tt*5iQl5u8jh;0OyI+Rl8XP}D;GSmGAH)pAi2r3+uGr3DA0*zS63bsKMcoTKiyU-'
        '=O^L2B%}0CFi3K0#EOZ{XF!n@^L?MsFACLHLc=Yj|Hi0Ei1{q|!%d9OvL1h!;n&vWc)NyjTM!6|o+++E}EDK#h3F'
        'tlOZX6arV6JIGu>X(VvcM=naz7ux6cj`cSz8DF1W09Ka7lN96CD(u*t;f9)ZW#MX?%n9R*TTB=zLQ?RZ$T=fthp#'
        'st<QF>y41re{0X6_OQpcK6hr@Gi6yv925quL^HT|NU6`2ZV?2grVxdcajGbaekC0(md3H#cV2BX0omiE*0$;jQ0X'
        'dPbI|ifcga#Gv0F|8qI>;BUpve~_o8@<U!<CUyBjU>0~X?yydrKFT?ziY-M0CmFi)2ZT!CQ@%IQIdL-'
        '$|i$(@Nln+tVh&>6W6qY(+;g5mbHuDf(&QU<(8P7PPfXlxuu7cQ~D1(M0RZUQ|_xUzyY>zh3^mDyqcdGQ<sAjs|='
        'zSWh=3mS{^Xwu%K7D+q(faNm=DFc2DR{RbhVM_j<_nSR&d>XD9;B|>_Kh(){!4F@%*K!CRtI*fQW?voC=lDt#V3|'
        '2<ZBY24BqNSA6@{m7PT>;pOPzSDaWNNK99FN$JQD#4k5zcAh<gLc#Vqi?m5@lVjIZQoK<x>|KWk<0E8w`+{{nQBr'
        '|Br~VM8gL|JgiIAMe;luo=O0lxr{`StF5~>QpBxSto66hGgvYi>iF%;XEriaYBRfi;nrvAuI0Y0k0$HPF^oo`X~p'
        'bKC-'
        '3{(EO4ic;`myR3UH@L!&R9<Cy59gpW9$;diBm5r4w5jT4qS=DCSKv&j551gUjkzTJRT>c$Caw@~D&drT9mGsZ>>I'
        ';$u%LlLr%^L!6aP-qVzqdX%ANBo&e{zPT$5Gl9@Tr$QD0dJ=lXy#f6K4p!a5ZKfO^UzT;31=3Y3@0DmQ|t>LN0v!'
        'rz}#T_2sQ-'
        '{;_Tcf<s+cY^Z<mt5w9f7j%@1r(8yp3=n>1q<w5Ta)bRVK^zG9}v!?R84MeL2xG<W(ng)eTV^d2K=&>wnH@!=6<p'
        'jREUT6fToX}RBX?un+jxrwx?naEcM4ukbDqAp+tOM&94ejUo`TP25haY@9Pfrc0M*+La$FGHl!a610#j~r^0etNO'
        'FxS1!=u(1{xcv=3v*d4CSNL80&givpmf9Gb&1EBd>|ygDI5b{k7QR+YTbGKf8S;cf##V`B$`ZVL&767Y^{xG}&gO'
        'F1?$tEBW4Y3>ul(EIAiivjs`pqcT?g)#LZE{13AJJuQM}6)rtxr#Y;eWV3qOCAB{z33V9muY2BE9fXs#?-'
        '*Yk0!eV5MRy~%hwlLs*DF2fgD4-'
        'AxC2OmRO5b&$Wf*`Qh4*?s$og9wMMW7#*SLSyx>%c=cg~>@L5q>u986!QBy*cw)FO23wasiNEK*L>w=~Pc&G_uMK'
        '((o>GMelD($z1;|9A$dMxHnL9n5svrK@b$(rmTT>H(JPu3s^IeP##+te+9c-'
        't1rmNPArPIWwA|vmzjNZAna$_Z9VG-'
        '7)%Z_9$Ie}5P6RoH+=ZG94<KIZ{;f7VhXXo;>SjErRwNbT&&LVQCob<)vmmbMC}`LSiPw;N75Tc&|hkxp<iOAzy;'
        'HVYKqWP4mkqhSVcgFXu5!aw;@n%1>1Mh)Y4&bgVD+&;|aU4#9O#|-'
        '<;yF48*&~A3_ZfU}^3g8H=LqWVjKgP(55%H>c**CH^BMGXb(KX)37b>69VHl_13066lUkW~ZNQBLuS<Sd<W#H8F4'
        '>)jH#rh4|*na<ve`^XVr$^Z8XhyiJ4mZImvcR&{le5~fgr`l&Iq=VX$yWs>|&vOB<9>wd0|0f<73n3n=b4q#bho}'
        '|)hu8#|0|7Y@wiXQ{4%!ipOna#5RROL@XNLipQexJ?heY{|E^u^t@MGyq)n;Q|tf?0edqybRx%P^R>6v^3S7N1cl'
        '7(X8Xg51J~ql@fCo@|lle?Ap^G#2xGF8JJZ7`V@=b*QVYLpG66tx9;(fQxaH$PY{ZEfYD3jPbcFHaX}OD4KxYnhA'
        'suL7$b;;v(*Ut&=<<fkv`24H+H3AXStBt2F!iX*r`DFuBde?|1MIjIPYxF6$1)5Oo8oW*+(e^JJ6Us`Vh4@yD5?Q'
        'AGTqzsCg<JvPsK<OytLld#vO#Yzp1hZsJ{3O|>3-'
        's3x=H+P0I!wVREU}K5l*>gd|33bM)=)|+d^Xo*CzPL$V;(1^6U=Rk_H!#Xagi`r=*aMily;)A6YlsGrgwr|E%tnm'
        'ZUS?wE290;Qn07Juf0O%Q?vMx8g}lBS?1m-'
        '|wx<}&*rQ#+_j2)nLFNy?duQKjS~<`51*^;Kr7L}344=$Z@i>RFgsGLg#>99~2Oh)oe|h&I{nW)_!i7`jD$$nGx6'
        '^#-Or8#Po)}#w=lJ(4_|ttmYVggBSS#yuw6EDcA^R?U*VOB3Fd3KaR*MU-'
        '{VX$TrLC?{_90kxpz^WAgHM9Pf>mX2J@O)cQIQpyU^H#h0E82_C_UK{>xPOL4o+PxC81mv1X>ySb<x?2!ujRJf1l'
        '^yzqmZVoQMX2p~(w&64-'
        'I4y2q#lZCsoV+F7M<6hzXU6WDmBv8~EnG~q;MMdm2FJC?1^bUqH=*5|P8cY2^`V7r@OQY53yCsK~Ii^P%dibJ(`R'
        'WE@c%Q^D$+swVag=J3u4c%H%mpj<ydh`}bdPb#|VZRk$4rlb%xMYr1kY(lsoUxF_8{VtPkllLj(&MG<4WmudmeQv'
        'b15T=NxTGNPEK&@b&Pn8bqcG$wtkh)K3;2}3S8|H1_t9|9itzAg!XU~dHf4~13o6Ph$^|E|S<0=|h-'
        'z@Ila!y2AW1=s8P2x3X=l4uJ|BEHTjJe_s_XEG(w2ASM-axnD84BUhk_Pf1G@swU5}-Tc&hy2N=w9J+kiGa<hW-v'
        'F@qA7#ir=WU9;b&LM%IoPL1l=`71HGm;b5^Jyop<yH~-X_aW@qi@G)hI8amEeIcV~-'
        'a8>`m9o`&DKG%;TUGRJ^37s2{MrCdV)EBJhW=Uz#&5iP0-'
        'OnqCV2P$?f0+FU+3@M{^|Vv<?wWwF)<m8KS2B4E~;(=_?4*=YP_#(`aA|_<za*ZB|2l0d*12thE1hsiOIz&{!3oa'
        ')&loO_`W9FTKb*({OI;k>;xGAz5&F(P}$2q2excG(Fuh#wn-Bpd2kGEuJ&#2`$g!dDfDwh6rV9~8HGTluns-'
        '5Q0dcDdm3Elv60`W@?vVwp>q69A%*Ol?D;#`AQi0;;QQh(38KbXG2(U%?5+Bkvou&&trlq<rM|B+um=mLwQ|NN0S'
        '33TdgDepg5_Nk;I#U+KR{h36g6d>s0X9%O%8u;nY4HM53<7WM9584XV;Uz7&M3p8F6)0H~%fZ;w6Tgh+_%17}%gF'
        'Q4}zshz6^2(5auel1(x{p9Cj&E6kimh8khV5%Z`G_{t(OXo@#Vzo<>o8uB7R^?7)wKeixA4_rb8q4}Z;<q?0d+w7'
        'WNzIgZI`-'
        '@i>A1=<vu3s@U2q^D;lJMF&dxFD*I6IsH_>KzY>0rJxY$Lzp?Ox)DkssY>in8#dKGEfB>`nz(V1}o`utDh29vpnX'
        '+!~jZn?f(hGqwu91@1q|KA!i^Y4PAps_8`KH{XE#haUv5Kpp}oo%yg)?Jp9Ysn%&WAhGn}s}@+SVKiqrJJg(<-'
        'f6~~jVF1+W0!<`N<>S8m8`%n68g(7&}rZTq4Jsdt{?7H5h0TF!;BtT4K&xsRx|!VHE(viuGHC_sll%bv?VWJ(~Wc'
        '?>yj?yhuJTAQ$@M2l!FR4NP^}nTdN!c`<z;gnSq7XWs#|#O_;Srjxp%wk`wBBxfD{<@BQ-$8MxUm$g-'
        '%n)j=dE(L|8cqBOvP1DRnTd%Bj9ud=E5TO5k3^X5r-1!u>g3G{si7~#Dd^m!!;vP5=t{T?x**geqFLkLuwf-'
        'k8~mN>>_%Pjr;^h+F3lJg7OnugjCnEoLZdti@%GCV|J`sX`1h3<;74ajP;A7`1F?lGP3qwok;jtO0rHJIj3rt{@z'
        '6&?_Zs%~(m=+g~i`=|nR1~V9kpJTR9Fgwvc)1F@zu`~KQ%$Q;x3aBFYf_80l;5~4cJ;w35!^}L_y(xJ-we_5#C2A'
        't4$JeYIQXtO!1QSfE>_*YVbhO*ja!9R(%*^vod5ylEsGOs{`C>Ri7B7G^NS8Awr+=s!QYd^?BS0pv{Ukd1t)>zx-'
        'd{*z1-yplF-hxnof8-9oca_WrpbE(-'
        'P_C<S06u&(T%rYfaAoNlb&$F$e3^^#$Ac(Icb$sYm%RF%2+v8VYe;?I(v)<*LY|K9JNDE+6a<y7p=Sb2tJlH9(`*'
        '!B;>R@5PHFMv;ARdWWV90xxkpA;A)5g8|4q>oz@KcVx@qive@2Rpy+$Iv6%7#z9Nc=wXi!<5|25wC9^wBzJ-'
        '0vD^jebMbW$`G?<>(P4(qmGdAbH=dWM9`Ec=aQrg@}Z>rjtiu?%Hz{ThYUNr3F-K)1B+~lhxk3-'
        'l%mT4$+PjZZ=@b5^*V<)(CEYUI9ZELr-ege3yjww@qvH~oJ*|#(E5QX^to&7yI`7vq^;h7|MA6ic+%bHW4{Ktpau'
        'adsF=?2K=-u;e|%?}X$?J`DFy#2JaavXA7JU9d!5vy|#bf<mK_tiWSS=O-'
        'o#>dQzv%BL%QGmr*tpAtqWF9pZ7Cs&wSRnLvIGQ|x*(iB7_|a)JFE2<lT{Qpo2&%YH?Ag`1i0mX=;OiOLqce$%^a'
        '&DD(AhsYb?OqgO*5h2-W{GjJR%)=DZ*?OC%hGrJ!Q7|l8|d{AgQAbwf-'
        'y3fF?c7LNG>m=duyY^>*dD&t>C`xu`W+<aMES_!0>X>ysBrWV7K5B;3dzT>N4lmLs<<0#8~*u0TAFMa<zZIenyjz'
        '|Sbd{5Z7C*;!;rV?|=b#wo^P8%gk@m$yavY6I{UPn`W9=Gr)A'
    ),
    '_portable_underwriter_9ae67b13ec77.reporting.movement': (
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
    '_portable_underwriter_9ae67b13ec77.reporting._underwriter_html': (
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
    '_portable_underwriter_9ae67b13ec77.reporting.diagnostics': (
        'c-rkfYm?(Pa^L4y@R%>+u0}hv-nFxe<?>a|mvZGEiG6opR4SSyVKls@NSUN&XS_G}xAHx|EZvP)<3UOq@3~TyOl_'
        '?s5NI?S{X(MwrfK?pxe=G*_ExO>%iC6nq}Xm-u`PO$Y|3I=H(g(@yX3ZMlcH)xv3b1g)=eum$sYbI*L~U4-'
        '7HPhi;LT~*(G^?d*~0X$n&J!?VGkwin?z4g6dsdsIpzr-^u#xrmBR3QrxU{qu&?%eOYg($@k*NgQ(X+*4`9-'
        'v95})6P>PUie!!c5!>m9zpfumpY>t4e@u!lsrR~QU(_2YfPedq#vdOPH<ic_^+vQG+OijI{;m+8e{pmDnOJ}E#jF'
        ')r2YQ)_d!Qa5r@Nb6B=GmmL$U6E*L2-C>hY9{e_xdKH$-T!yxEA#7G=-'
        'CqpbIbzH_novu*YrRs7?gs4P4EOHq|TIkAz?z9j(9>wMSTi=C)@xBI*=Mcx&+BL5)D?H%-#-'
        ';}y{%R0Gko$rgsswp;z!^Oo$+$Of+P89XzzNikOo5SqQVA9&Qc$_A(1~1E!%de7K0MyT^r&a(n*0N**)rx!37F(g'
        '9X$ajyerBfcriF1s*Xu)jFXV_|QV&JtAVB3L4q<VKn=F4JKZ<TG>J89up4>D|1;a+n`@_BxOFl&VeI-Xkm?aB*P_'
        ')|)C_W(!rpf!V-Yn9NCN9mWa(SD8@UhOQl!Kwq<$Qj5y|Un8-~<z%)8~>(-'
        '3oGiP(yx+Rgn~fD)I}ja?>1eSS83Y4W-'
        'SOe`*gf2&ez$^?a55YT*?kt`f?&Z4P@0V13wihuy@&1$rjewid@2ssk^sp=v*&hn5fA(Pd71Gn|v#Coeo&NPrJ!%'
        'vZCkDZ}2yG)rE2xX-XsCdb}`QmrgbE|RjMW&x+_my6`evVoG12g2g^P*r(Vz84euyDn-'
        '8<M9~6YIJ}w?`w78cJZjCYg^W3-l0(-'
        '>oP81R#}`TWK57q?32GGe`so8E&fXh6Cwp;^Tb_ZGG#sM37%R}S|GnVQU*wr-'
        '7O5Q7n8?qR#ep_3n(p7!T%+3iVx7gR8QBlE8yAJ@c#>h)wji7{M3}238;aGOm?*wEn1Kq5Z7Nv2B1I3kXK-iV`2K'
        'UU2ClBrrm)-'
        '`3by&1&s|!f;JuqvaXs==*H887^t}E^1i7S*W&W}ZI+0t6GVwu8Zu`bcrax>XdV)1Wpe=D<sFnyBCL>T`#cYA@~E'
        'MxL_N_m2qV#8X4p}FQ*<S0twoZy&4-+{Kq`m8h16J*o#<QO@toAM<aBAS=R-!AS&4n~L9}y;l`OHtMq{Ylq-'
        'EE)({PL{*#yztz!(amgwups7bQ6R&FnYeQT?_pc4E%tl8i8NnroHiP-dFZ)K9KGfqopqS6utlsBo;5NiBm~h-'
        'ScnolQBI%mrab$7MXk*0drI<p7eJ_a6jwFANBOL>`J$IVIWD0p$$aK9X1>Ys};LDrr#+2*zy#b6SB?Tw-'
        '@}iok_kt)SvkYEyK?YnU6ZouGe>0(Z(m5A8axf-LU<JkCh7tpM)`pjx^j+uQ2E@QCQ#8MS<lgw5-'
        '!;$zW&XiKW{u4y*;ZLuq>$0L=9wnyr0$_|u7C)s7JV%Hp6m&D<0M28`DfK!KNZcmbJsWMwPHOThOfyj-'
        '<FHlM@V=#(l4*2XS)mX2x>=+4I1I^;}=p?eT#<u(@omnecW?B$&8Pj`W$raQR*>DxrB;<>MdF9rCTnU8eyA+-'
        'na|s>*t*R)bLM%@Jp=5XlDi-Xl%R(OmhDvw1@=NDZo+FPr)u5X5J5t|KEeMwXj?~|G;;?D*_BGTE*&Y7^@nYJ+Rb'
        ')y*fV=D3eHVwA^^d|Qb1FR%mv>&d{RWM*$T*QTV2H#z5vsYogmiODB5e#~Fp~rg*{`uieDy0Ex~vyz+uU>l9J>wB'
        'EjN|j9?^L^2F6u&(B3VGv<P%jIuG^Jcso)%ZZj$xZ)Nq4+tikix0f2oZ7a*%c2AzQR(>FNgC<I>!@$IkhobJwN~j'
        'e~Bt$V93fQ;JO>t9JWnW@59qN+H7VVIcJ0MF20{}Xj5s3h(g#px;mCjts@5;@-DeK-'
        '@WP6Kb5YnsJTejAf<;sEWN-~cCz`%Ot)nuzxMgFA;*g$>J?kAR1xctySO}HS-'
        '$T4EI&?j=}yVA4A#1ELs8t`*{^O^!$b7;}4sj^O+=f3GBMt7)y4F;<LjXpm8Y%dR%hT#2oM5&vi-'
        'h3!G{T=uo6nZT0MGoe+bIjYeICLH8)BOELxQ2k)yi*)rNfw&qZc(#<pX=mELP$%GV|Lo74<NJ;GcXV^ITKHxr)p$'
        'SMSUBpXhsfIEfw54E=f=wIt5;BBkZZ1!q8;?RPN(;bdv6`uG1-)-'
        '0Lg)cq>2NsgHMQ#BR|VWk}V;{)Q&&#EEkd219*~=9>O{i~qf&|K1HCI#7(_weBg}5LWPfU|ZqIS^g8V1gbaW*>kn'
        '85o5`(T#(1YuquwEK9p#uY5JW+w@A8O)1biJ9J;a=U3aN*PX0~doV*upEh^2zi2#=sye2WbAYgyG6P9Jsvnmn;;`'
        '_3?7vP=%T@IB<u#0WdLxT=nmI~}ba|=YrZH;zAz{pb~^#O$mD8xh8C*S_(cS*M{DltovZ;)=X26Tn-7jS=|C)x-'
        'o2uH!_2v4?cxdAWkz9})31aOldejuIlkf3$0ipNVy(jR_E0I6mzp`%W#z+wrdXS+j7E*+}ZTM*)=o5``?mUU4j6v'
        ';xAlsncz&wZ2NqCF{EQOq>qSv1rbGHE{CcntZKz7pi^Uc7h>rpZ{I4n(fiaixqyiLVdbErm?+WUJRa!4`z=Lbg=C'
        'ZWh^;kfJ1KHMcXmkiK^JBe(#&;$fnDBR^X;`|&kM?~h-'
        '+b?~*y#6^0Fg8!Pt{foB>fMl7R*ad)05Y{Dv#Rc#6?6WuT)Gi1-M~W^9B+a(`24-'
        's#B0qHiQ<zOw|0=m!S%~B|)DsDvYN?KBg@A*G)x?D81`Y@e`}H(|b;aircPm8;R9;X+0)0U(J#CLMPXO{FnOp)9l'
        '=r0lZeZ1|okdBt83IA?NB;ywv#?{VWmH?l6nTBTq6Ytr(O0FJU_?wgI%A&VA_+$hV}2*=WKxM#Dh`0vY1QRoPN)L'
        'vpONEcu#(sxVENic2b(1?{U$od=PdiE_o)QLT$2DPlBCPz4Mm$hEI1}q@1<YwLTM845J6**yP^2y&DFclr_{~cYv'
        '71CjG9^#Y_@vuse*R<V(nr*_29mQNsz){bTA{iY<dT-'
        'N3(@Rf)OOFyddC#9Gm7ufv%esUH`Zj6C$(SJ7L~40LwKS$;lwd%j*>oO@6&vDfLipcZDW_WxrPzhT3n~l!s1D0T_'
        '2AmOIeP1dDMp*P^T@Z)mnH^i0vOxxMW~-|2M-'
        'vhL(kLZ9khULvRsj&UK!NG+A|qlV&PkJ9#5?lmZNs6oGSy5((OEz~!*a=4Xo0cla?YNe^~8!(p>Ic2g1jIG&-'
        'MT*tc5=k0tRO51PIHaW-'
        '%G{30A(vEDYf<+tv6CE&nkL++ga&HP=4z(?DfxFH_KB#Q!}cy|4n25e=;buk!PrUdMM%g+bt!ejPYu{)aWCrR!=0'
        '!Vv?93`A7CX980-Yk%79sXFUUE-5hW7D?y$Z~fFDFV<9m?<GJssd)X>%IH)<jrLaQ|zEIbq;rXEch7fzE(-'
        '1ZBS{uUV>ze<>B)w!XxTTf;^qc@yzQvqu`y9pX6;0}D~Z9W<p624V7y2LdHX0hKDJ8%Y1$^<xfr;>T0>t?qH>)pY'
        'kl(r?-z@!mh7R0sO9d`Lz0E=RTS$VC&dUQC&z^*x2WI?Y`i~2p(H=F-'
        '_@p)_EN#lEIpQ_Q9_r>~A>!4i!rX&z7v{umR$C@^ORT3qNeJlqYtTO`|ErJqlDUW6c@G-'
        '^p`Dk*$SaVPlJSRX#;(pQ00NEwVu$>tv3qaxI<^l}m6wI!iJ(lO^3uIBfM1ZadnrDzl1`tQx->X-'
        '2P&@X)D6Dof^w2FXg1F&FKYWp-'
        '7_6{iiYKjCNT2Aer=Jyj8dD6O$YYpkC>Vv$Fd8GbB{0hI@#*JBqyB*#HY$vy@m&oClqyg%^-nOKm@bb5M-'
        '&Pd=fqcz#8sl2Y@r$*QFCYOH8&a;)sgzoO$eD@jD&R3Z2=(upNgYY{A~eB;|LjtcB9VOiF$I9fuxM(CrH)tbPX+3'
        'H=<tO?TYq&>PpmU(lo*Y#~;O}|L0Eq+0#BU<wHWlX8I&y`9DG=PbM5HNj7)*_~J+eIG(k0ieD}^kw;E~6<JGLMO('
        '_Mpk=|PgcU+7WH?Xd*uiqyK+pIVtX`(5e2fM9E_2UxsWtF!-#<!!CDIkkPoQ0|dtvfvarMKzE--'
        '>UuAd@6mb&fAH=gDJG?Y1iW(4dRtY|4O@TKe|lgst0*<SA_s^n5V@;mtZSPy@9@e&m$*y||4B#0QL00o0ojF6e_1'
        'IO~E>gh|jBk{0rYEkR1E)zFvW`xLg8B@Z-'
        '9VfPJQ4@>Fro@E2MOtn_p^Fst?mfDArX+JSlIp`wv_;>vCP=coo*2Xe+9UDVQ!2Cp$F^9%7sP4?>Z^o9v)?Z%n#g'
        'kNM4>mDZ#q5EUt+BBjpI+l^ZIduwY`C0>>rmP)O3jzR?c&UoP6TA@%qn?4H3jJXXK?b3K_`7Ry29C(KPuC1@v<!F'
        '{7<{(PwdhZxG<?Hy*@nh-po8BLGt~ZwOvdBa$@O7A34j{(>RKZ`!tLC#mG!9d72_2>6Ezu}-dOljn8nEJ>i-'
        'UGacwoOT~NQf(87n;V{!`v$>Q8?3=ZUTj-'
        'I2Q{9pYEQ}49@<swKv2ZSZbAJHRv+u8#<UFDUcq6PeV4G~Dwns#8e<g{W0>iEBE_!QdoF;bDnHp9)Oe7yeXZ7>=j'
        '=4OS+l%W^0n6AZp1gch-RUAP0jOYYt^gPQpQFxY`k7{RSWmh!+`@1_OlFLRzx`t*^x1x0?)%W4szWLgK{w9_Gb*>'
        'M$`>>KS~Sx!+#kY!%NeX+SYLCNPA1KquV8{vuKW7z>!o(8-'
        'FDnEONT8%Kbzt9Y&Z}iPO)eX6wvR7ZTdk1Ex!_Y#XH}!1b%qzXgK^3JlkE6P<O=bDEsAbINvc0vfc2&v60I8$o4N'
        't-'
        '(#xN(YLZjQEHP7t645PJbu`Ls4lK_tVO83CJ&1!XB)DF#Z8081leTts<Km2#JRPT}blDX^_Tq;wdye^~k{*4ky`O'
        '9LamPBRC=H-4br<#K49VoLusUnNCO&&IA`>ydXwd7JD)Qpc9CELQ?W6X9YOTj-'
        '3(kN#?o=QoeF#(=a~I?XH7i%p~)UVhhKiz{@yd<GEUAq$sDGTq^WUG~GCwYV7ODXJivUE0frd*@UwLV~9+d7k6|f'
        'iBeH{!Abc}1Dh!4<~p6Yz4WZ;vcF!oUYpK6MJKmAw1PIr<?=}FeqsV<S+9GBAZ7S;#$i*gtJ&O_+t$!KnkJ|UmSP'
        'eeT}G$1z_`B((f5;qSmuC=WjOtsJx9L<tm*^P3~2o%+NL9QE$1oI8VJxf=7RRf;)kSztQ-'
        '|*al4n0KHQa+NH7q^(kzM_V0)=96^U#ExnB*0AUeA`)#2ae5dtqY4XC@7q_@iQf&x^(5|LF*-(k9%vTd-EuA3T(H'
        'erZ;IW%o-'
        '7Y9j9ki2!LnhHeFHi4x9ZYm+`P#cpvp#Z81&hc1s_%Ua#&vpB2wn4;OAue*fbn<u<hWxyAVEM<AaGN~7%y0?cEe*'
        '8QimyNnF|f@!kX{Z!8X5&skE8qL!tIoFuz}5;h%Sl&`3I_i_h}g^pK1|uS$wLd9_oXK)CqOYH8?UVx*RM~F8SIX%'
        ')~)N&Wh?2#21E~W0goL;)c6(u++*Hb|Ui{d)Mkwf+i7c=qWbkfn0U|U6DI@61H^@u*z1pEK(mA&$*Om+rSp;j5A5'
        '!O>@9IBS0+rPqwl7i=Kd$Hxo2{hp8udEA~~n26Q<-_HidL%5m-'
        'v?9V+JK;AKm2ks_^8?f1MjKbMC@Y7kjBW!&<>}<|5Vxf%#1=g3!!bR86?%uJ=a+O}W=}+$%v#>wmBWGD2$Q(uJ6P'
        '?G5VayM}*6xAX5Nmfy_MDT_mbEOeT0UTmYPrESG4wjx29$M_$8FN3H1P*obHsO#I=6B(cP6%Lb;2f;&XO6~=K@g!'
        'YrF0578cdm+C`Hwzj>tYg7u4Jr$MC8Lwpc<BPG$@=#i0xha}FDCii%oWRPE+5<}woDQR({oW|%Ojo&X#l=vAQ=m-'
        'pc$L~H+>R}*);VqT<`Rk#JDuz$nIz66puJ#w6uTVSUe3>btUDQcTvAM)^0#0O1V_n3pkHZts>X45$GRCc_`Nm%he'
        'ps`cfp1lSdyu#FcH+7puF*0WkXE3K>==69T1h1+V4|Szol@Sm;6G2Urpy{l6Uqs&1(}z907ac=1QhgXlv}bGBEH+'
        'Az<$jwO`NgJjLrjI4Vgzqw3db}tKo|u*x<enY>JAEz4FjMa@dWd9JAp;a}C{Ut&l*WMw7^8Bjhk$K9?SjSqX??QH'
        'l^m?X%n_`=Z3dz?5hSc8w)-'
        '>MiSBiXA#NJl$JwX2c%9n7XQ7CqYx+XIv3A;xa{o1@T*+%r$XzI3uEEwDy*&IOJBlGTYo2bzjJ{D-'
        'z_=Cj=f2QIA{#uH1t-'
        'Q**oqBvu~@o7f)cG}x6q4))HR2MaGtlEH5EOCI^Tu(5pygNTR%>#zaD5>lTWE$5GRK<ep+3a9JEB4n9JiXl*;K8V'
        '45jBv>{NaS!EG154gJTHM_o71M6%7$*X6Q0Jw8fSh?|5y%w(8by5nCJOEM{+37&OOWGQzV5ddcTn~P1(>i4Fm9}D'
        'vMkrgsKb)KNf28aGi#|#~{0$6wc$ZwXWA|b}{Hd(ikuV<P$X(mU4W^;ECHyQ5V%C`K0ds8Ue76QJa$j=iq7nDF3i'
        '4R?_(?$K2JXY;FeWH-lx{kyK`t53A&76w-*4se28STVd4iFt{iL%!%XID8-'
        'C|d(V=qwFVCGzj*O+@RERAw)>iYqzLU(Wa!>8p(rHaX=?AEFc1n$5eaq8<Pz8qQX8*&Xh6dkC=3sk-JVlpj3+utl'
        'hNi;HRG;{F@w<+IrsS}{A}>))9`H&T;vC9ovR9XyHK&7(vp<P$EQ<ons^$~IqJj_=I|)(GozxL#|h~ZSkyGFx}m}'
        'x#a2IyPVPI%6y}T_oidIPCAo~>*yk?MaIY9STj4e9o188aN!2AoelBQ`rXt-eS=;8QgtL#RMK2;d&h1Lk;!c_F2T'
        'N8No#-'
        '8IrfyNeb`!m?69Um!DU1N}qm2saDF54ypfSH>IgFRu!5r*l3}It<V#yQ(we#){90R9~7eyZdp)!i*9y<g!ZI$W6x'
        '5psrGnvwsZABw5F4b3*Q62^!*B+e&7n_)A^bmR$wapdv{4OWz=%^NU5OfU~Eh1(l@V>A36caH1_v%!@fe$$fdW;A'
        'WkAWKt!y2P_>zNvLKUNp#+nkdbnI~|~k62*7`xB+K@<C4JG0*idLAnvAW5mi14|2@sIPP~0`X1*`w?FOU9?j|~tn'
        '6qFEf~QXX1wXs=+o2OmSc{@h=4sE3EvrNsjErG-EOzWiO~Wc<v!9yWU<H*3|Ye6U>(Mp1qVlvK0YI-tPO1s`?lN_'
        '?W4Jb;3)nca^6B#UKDil6b#1&&c-'
        'XGYXq~{l#d|fgtc6ZzFZ8WJCB5YK8RL6%qj1dpAaH+gC=*NOoKN5Ajdj#x^VCt?JF4>*oDt$r;YR|*3q#Zp^rP#('
        '@>6#^%N4B<7W~<uulh_B7J&lt<$f(!Xdc7m)AKX;nryf>V%O7Z8Lv5#_VcCAXnjP^IONQ2R9Dl8wjDY_xT{KLGrq'
        '=Qac?NP8Vf<EwYDv^hR}w(z;aFaHrp@Hkc=ip~Fq;@q5@Koe3R<dYgW9$?}xk7Wd7e9S1Mb{_+&?K2?W1=#CNq)2'
        'pjP2fXgKb+-*7x^@w}ar;J|$_{V$^p>52u4wAWBvi9LR2oz7#<NZb!-t-B!aQ-'
        'mY@ltZq@ZzFIM8}Xhai0h9t}Y9PXP@3v;KzOs9hd*sKc$lm>Hd(6Bmpuf$)B9{rwmXP3v;EZ`CWUMi--'
        '_@vo8dVb8cs-DqX&6}~#|cN}q%Q`gxU9qW-'
        '*U5qCNy}RkfsR7m~v_MZx|6yU%xYv7(tdS*|xu^XYH@c=k2F<tuJ<^IaJZ~j0fg2JRsio;AX8CoXW^Cs?okus+2O'
        'vblfzh<Y>EOnZcSaGf<`_D;7+o<(ErxOY?ZLH$7dx5;JUJ57adSu)?$6<7lq0>^56^KdW<GQczCQ5fEvgot#T`Df'
        'qypI!x`lr3?DW|S?FZ7J<>l}BUvWZl&sv3fGB0>epd+DkbH}>{K$}E!?1egq&$-'
        'Tm1*Wa>V%oK;HPxBn;d$GSfa>JEc+BP;HYTe{)Zh`gr|=W8BVam{?P<6-Bt-HznTHZ~xr}z?^syR-'
        '&EAL@K=!F)?k3Ad;Zb^6xjq3NA~_08X2u18)P2Fm_^JEZs5tZVX%sHLT;Ok*1_b|OwojJWTZnysoA+rhYuP}rb)k'
        'BUzPrsiDh*5_t7^WJufQZnz&QY6Uqt2{K5$<BxeCq-aM2k&Dd1GH=`!o4I_xM3WSQQI0$<6Bcg^pLEztC^p&xPsV'
        '#+VV-'
        '`r9y(cd*2sv=*bVc$JvRozs5w=Y4h?VHkqd*E<Zo$517tN3ClNW~$k$8gvXoSD=M>t_E5E|b`^x7;Zd+>z2oq*f>'
        'Xfh{Ony46?yyQGw=v?ReA5{If;FXvM|3#%D!GUjT-'
        '+C63GPKlnX)zEE9OL?6Vo%r)AIdA{)E{&plX4Gz`cWc$KCf^k$_)bKEyc76R&51gbY0Bq=ueE*g%!>&nTsrD$dYP'
        '$@*vy*4j<U`&rGj*&Z&wEJnbB~>1F{0KtL)3wEFHK#K!*;GS&MrK`^r4Qc~ptjjxthcu-'
        '$FTP^z6bCUqe#XHQ)*Di7f$Fz7RF8_>x`MUd5aI+(^E4`nOJV(!3E5*rOVWk)bUVPg`Ze6S3?tQDyINq7ho?Jm7b'
        'neBzgXhz$>f5%=j|1hDMV?_#-'
        '7Oc3M0T6xKZ?b6{UxY0s)wk1|p2a8jWh(lpmCUEc)O^`K%d+6&;e~a66ndF=w=Ji)J{4_IkY+JN!knMR+c{CnG46'
        '0vv>j>;IWCME&=+;#sO;{^C!Aqj?;O9%6GXWBNOm6Zga7svjXyM!`M$Z{*gou1|8zSAlOpUN^7;dtqX!^PKn_c8M'
        ';q(2@Ag__oyhCvVlZl&_HHEV3=GVKM}`)e{79{(d8f@;eBjQ7W(o~z8op8|+BF}Y*T!;@Kb2b8^(!bWT=vAd6!*f'
        'x<bmA)=yUIdA6k(w`_Z#O7Bq@;x-QMK*GM@1UU}M|3S-*e1*TWS8kqd;0h5JCfSKeFpPXET^jG#Yc-IkorY77WzS'
        'v<3_ZnZ#Ug4F=X^#3K;qMkob)|u}tR_yRsC%<o=FR|r#yOw&<hV}rh&7jwIBxotZ4PGMJKNI0)ZkSdewkO_Xg*cf'
        '{Eont!*!jsAc~`GwUz><!!E+D=P<~OR{|b5(g0v43nL-vRunQE&1=iT*c%<)Ipb~kqro@e>B~1G{@>7)#~i>x-'
        '%feAp4L#M_GYY*FX<FpEkmtnm*~#CG+d^;Dy%R23i(NO;3>G`q3q--cGR3q-'
        'FWp{p)Poo{yS90i?c%gYhnF?5KV5&9z8FMuh)pc*;c=m)rS!Q$5KS&tm${U4Y=s|?t`RuFi>vczgPnT47(BCx-Iu'
        'q50_fvp-'
        ';l&fhi_&9y$Pv?~!Qf*uFa5L(4(cLv!<2>|vIUztU@LcEQ)^OS+{EQx*m7B%C_G=|?riPsxA(SE3*#4ASV-'
        'e<wPappL&g<2VnvIzGY#|8W!xZ~jj}W0(WN-sFqJ<koc?f}YYkrO*?YUJUJR03#k{oS!rA#d>|%9jbz^wZeNfRju'
        'dFK7*(3A64*1dElF9op9Q(j)?xRPwd^B`*`=m(>>G;&JVtWg|1x!!-SXW$jdRi|1I-'
        'vUiX%pG|uNvwb<=Tx%xFg6AN^FzD-jt8=pYrzc~jVp94(W!4|{p@Ta?yLJvhfP80c3zd(~qT@X|Lnq8zCk<<CJxg'
        '%T^49%}E6~~13n83R8b(-@$BjlW=#xdd5GbQImUC(I+)F4SOG(-'
        '_Sfuv)u*_l`EoEVHgKZqCI)VX=g)tsLE=G*7Sn8_hgz8;@ld$*)%%brGFTH@jj%+aee_!9&E<5T7Zeh0&)&Q77N^'
        'U2OYI>QFErLf}3ayx`zh??Ok7$mV>+SQ@FL{k<kNCefKxq9MZOS*<l!^@Jd{M*lh$mK<Nlne=TsisRW6SOk;Rr{3'
        'O6^IDMr1}!~0qg*Zb&FR?$k)KkBYNy*g0ejOYlCl+1Yr;xhHe(2sMb)1aV;g6>T|`(&R&M2N;;$qdujm~5vFbSLT'
        '0XOzBIDT9@@>z_<MYOWs3Z$ckv~JnVZ^%t~U4x6m^leNZFd|(Ll(6*NlY>s;19XWWoWe%VUdu2d2N+*RG(Av+?R-'
        '&;egfn->ovJWGIkb!a`ZIlu5w-'
        'CkvbI`r~AsKzhY;a!>z!kbE>k((&qIzDI;2HkSLi4YAa=~(^%cpZE8!L!|kQSkb{5ffesxWui&CxA-wO<8Q~hTcF'
        'EI4n_=gJ$u>%AwkWhYG_S9FFWQz(WL=A5(42v1mp=rpnIiLi+I}rM{3hh2uo9Ry^ugv^Ch)DE;&^Kj6Yug4P5lS?'
        'fXdpq1hYmiJH>_eELBtPL+o125ucVf0VD5o|~8UE(0I_v~yKQ<IrqCo9x2OU_<R#HvNS299Z<0Nhv_qvi}8xZo6~'
        'dd(WTp^T6=-iOdtpzkR-Myj(wJoH$ff%qV}b+IpQ%8GU_7Ao;ejV6un2eX&K$uEE+>jjG0FJ$Ad!RIX2Rnc`5SZn'
        '+wYPAbTMagfB$bK*Qe5Yyp2N*xTRa`GsE}Ob~1S79rWeR?9cfi+@-'
        '#qHION)Vy76gLs3RX7<;*rJ9O*)cpu}Ko}<j6^%;P3mPV47DMCC0vUShMUv9o$GWN4JM6?NqMl&~tii)NmK}!p&F'
        '}sa0StxTa76*O>o^#X_@JL;bUT3x@>w$Gy7qjr7zA7yPTn72k5(KC+doUa-'
        'm*bcu9xU`&9SKHt9jqq#SlU%=rg4J&SQUw&*GXGw9MrW;Xo{N6LqU_Ax*lt%8o9DDbbJu@+QWyR11@M_*>^bTTt5'
        'xMTc%P5Rpk$LJ1A)V_zNl0nMB){gpy@J<{VS3@_H=c?npZNv<VXJUDFZd7sHUpNQw1{SQ>3Pipwc)P@ofUd)gu+R'
        'kiLV9q_($JntMqm#ViWe>10woDecCSV5Eu3<BN`jvg8yI;m|9$ndNa%obM)kbAL(|U#MnIgHablw-rBo#i1n@&@P'
        'hTL%ffkM62_SP<QMdveq)k17K2fE`OVpk;t@bvm__V;v}X`ow*K_kF$=dCzF+zru3#`ibkEZ?Cu*A$G>!>6MUvtz'
        'jV;?8Po8%#iX4Z5H9p<6VKQu<W8ONxk#s3dd#I39L^F-LC-87}@jndEgl_'
    ),
    '_portable_underwriter_9ae67b13ec77.reporting.report': (
        'c-q|>+m76}^?kmA(Ua6_g*XM8b`TYH9H$LnCx*Rl9u^BhBXM?=)vcto>&<rlz31>Ek`lEucAB8A5oBk`bK|-'
        '5aDpIsRkbu{<i2CK`?|X)`;L+P=7!Ome4wQ1N?KnqdRNhV!f4;IfhR!_Y&Lt=H6+XS<1jLsWu$6wljLpN4f#-'
        'YE#GX^T9Xe4314(|O$)J`<hw#6z0Ui-YHwolj{b9`Z9ye;nGbnU=bTfnA*ZDYf(}(f_4fPA7xA<xL3&_bS33>yW|'
        'C!iK%RR2dHXQQ+vjbWa{~YMr9LQb<hz<?V_Q;o&#Hm4?9Vy<<CnW<f1t&eUnWvJKr(S)4ntFGCXC|7V*3+VlvRGy'
        'c6_LcNj2eyz`t*%jdx1Xu~^T3;$55Zd{5PPMvIP>YPZPiVyr=LnMF9>M4uoTxJrp8bj5n9R^Ot5`5?KzM(5Hya_O'
        'z0^P+19`awY{pUH$PW^@Ao6yd72ABUO7UUc=?v_G(a<TZ#EtF@-jSp_P4-&RVFH>?9L&E-R{WPNY=NwI(EErl<3-'
        '%>u-iWcyy&`nFZ^_>t)ZnYh2VE1R5NwKp^ZAP0-_U7#mU%z_!I(zr>_4Ds9zkBg+t7GSi4=i@S!2hnVNlG3C-'
        'C)mTa6JTDwIr4q<vj>ZVKsPB=T$=tU~Is8M$1Y#6av1H-'
        ')KpSb(A|)tf2eyL*H>o6ZUQ~vOAi65NyW=ov*s1gepkF54jKiVFoYQUliTg4i3su{s}m}qhN!RXP)5BKC%zPoLEv'
        '7a-BZ(+9A$3H}@ZVH?lUv-Su;S4Io5-oN?rx5BRsV@A90-'
        '&1Uo0sT_om3x1|;ddWr_ZN!pHFR!XwT33gzE8q3B*h=*T!6nP979!<hUk!M`vVv%-'
        'b|W60G<3+3vZ#ghLtYHz(A8x(f)J22F_DN8h_r@#3QD4oh3+Za5-'
        '6ehAU1$vPZ<Y#dQ~pdJycCl0tR+9WLd~*y^qMnU&!}eOSh9ksy(TA)$$>SY$t#chgVE?T~|j20sq0NI3<{(UNY9P'
        'FmO;vGlCv>l(b+sRuwTMn?aDFc^gDeu{NhUkFSA0m#LI6mAdkr*Fajd9dNVm90l272a;5Lk1D63q({KGxc4mioP3'
        'ok{_x?8<a6KQM0t2ptCBi&KoBn!L0a-'
        'meET9eA&@0GN@X1o<oW!xJRWUZ!k}jtL;V0p<P}DhD~?ipDine67PZgB>M8bbx{5=oB=r<)WW=6rUwxo9x%8REx!'
        'e5&RXxcv4$(FYOhrOWT<r!inVEkb(QpDR+Z#3;5q3pKSwU4JVT9$f54aQce_l|RIfVSn1%b}-`dX%?-^o8Fi)L-'
        '!AWhxZBF41_6756=Z7AKk&4tJYNMTim>#f@>l$n$s0^%wJq>$zJf_Idl_4_c22`+(3ib$k24Pe$u)hZn%;5iKsqi'
        'exrY;W7{9%Jnh5d^lx%n)TE!;xG-aU8<A7NiBi;S@pRRSS=D{4H463o21NK>p_Pdcw(lH5@QI8<wE+fc&0-'
        '9|XxyUDbvhS}9tFig#q(Nq&O5M6uFkIt@KK{SpL0>@*XQB#z0AIHfV8Bn3sbtM6#JJz+v*augUwqqZ#;ie0M>8p+'
        'FMmZ$~sbmBAZ0md3l>FYB(N{`vTqIHRGhZZ*;b^-dEhp`==M~7Gg=>u38VkeN5gH7xlV#dJ~Jy-D4{-'
        '*!!myUNOBH%N2ye0>@9qPzXd`RG>v+jjTz$jYaEso@>=+`+?#WkCcKanfn$rC9z^!V#iaK{x=ZS<>|i(JPGM62)^'
        'EX$8(D3KKmoIc&(JgrDwgL7~BfM9QAOu2P<mV&?<*eGCAD62T^x*ZW#XBX*2p?+FwNwe%I*Bwf6Adhx_JI)#hYYY'
        '1a>((J8o|-G4>|dSHXKg;tf04bsD!6^w)c?%8vK8~|1b&5-F-'
        '=dIlF<P#LK;B#6?f`3pIIqe3MvX;=<O_I8*?3#I^WTHi&D;R0UTuAVx|*agUYedR55e~H+9>nQ>>@N+X*<WsKOVl'
        'PC3t`ko0J(Z#njLRp6M=99))UL3m5FZ7jb*PDx&tp^!;wa8jTec|a}i$05VfU1)t4N`m$aXLv$a_+h%zy_HrGw$%'
        'j5aG-'
        '?AnG?wN_siF>)D%<91;sT^^pt`LXzb05Wt2dK0Y&I%Sr{eC^5N9WNYI3jduVo(8vQPegy(}+AA<zPdm>rFhv4``%'
        'M(~krRP#O2M`e?Flh)9k?n^PMd=X7qz#V2ln(p+0j@@+3?ey0+CDXRa>r}FHds&URNk~Eh1=D!W7n&0Y<*ZZ>vpl'
        '7o^1MD9ZJ}7no3`EE#7A20nr^fTrJ_!^&r5Mk&z!|lZBPatYL`0<vSx1u`^UdjdKkpd?LQP#Uikip9N|!<J_^%p_'
        'vLYbO91Xk`grIGk#7bGsJYB$=r*-i_E%vo`HLofLPNul%`Jh4C8AC`!i)-'
        'c2BFD!;lHQ3XH}CszO_Xm`mIZd9C0AHQ&&j<tl_k6Gn3ZZfHvx`d>B<1t98CeFE)J`2O-'
        'm1b5<YkI7^RaUC;n3Vk=&xa7e?Z(X0=+IGV4GnfYM!OhrY1+D9hLx!^87ke{Y@V&f6{|;m?A1>#wS3bjETY?^~5t'
        'qEJpq(l{smr>vM6u(YOmfzf`p^ovL~Yv`a;S~n`@*A5F|x>sp?PwkkRu!g&YCwYH3mN>0u2+BEso)>?~YytFe=7+'
        ')lgA!vgu92IhzgT9I%DtkxNyrW7|+RwmspK1~oX&o@1~(+R%2Gf$Qb@^m0yCF4{75BW7s0Yt2boJ8HtI(z-'
        '~QI;UePP}ONGN>!}0;C4Bam~|7PLSj-B1yYbD*jwW4<U*BnNTRAbmR&L85oZ-'
        'L>2rpw&23q+P=4WJ=o&*S3R=v%TQ!5VkmMQgMJHT&0Shf-suMx(fD%}AB^)XZ#$kW)r$F}$yRoXv3}>-'
        'ZrzPc<)lTHTE$PeT8_4h9;x}hL1Ku&_&~o`+ew-14qf-'
        '}J6+xaiJ=jg=JU_)f&GCuUKLuLpZsg`!#TYQe9U&EeT*OSZJ~r>!OC0u<x*&D?J+zqfQ}`GZ)B6~hvJxovgP9NIW'
        'G66368^jLiZ;3QkHU}hxfh!UY~|15sZctM>QJTTxz!-3VygrNIrJyUfNMhQPEfuprfaWv<|?x{-'
        'e_Dgm4D2#<%OyB*#J0xmpb1JkoLS(e=u9p)T#VqmS=WNXWuP+dHi&)H3<<ZClRl>pcUs;cczQfZdewIQJYWcXIV!'
        'LoYIfenRxW0MOdh5c7C|rmImCrxr)1nW??M)k%fAnYFX?KWQl0+8k`a`1y*f6T$y8?>Ohqnsgv2>6nQQc;0gZ6{7'
        '|_{JY_D7xyNI?%w*C0?tw&ozg|%NRXmd+UIcpN-'
        'T=?Mi%Kkg2T512Uu#m>zq42oX|426Mc=s$u4GCRZI<w<B4j*Iwv(x+#WX;s$xHpcp8=gNCFv7alC`@=de&XU?FH<'
        'H;{UM~;A2nOP2I@A;huKSS99U2g+p2VZP%{rZs%x*i5Gh@YcuGk4h>c|IP<YgBFM)jU!(B9*M)qIJ}8C{Mc#I81q'
        'n$v9{4n+xWZx$O-b=U-k~-B_UiSN-'
        'V*ua09fzq3R)EFB~?A_L90y$^`nL92MP)K7Jscr)Q=eCND<|D&@Y;D3I<h1!&sEXj254?h#FJ?Tta?4&{iCU<7`m'
        ')fQ*!ycjDC}S8heLTg7t9Ruu;zCD~jkQKoc0<hPXTs4A#Rf?~#uq>#V?t`8j(y4&YPUQ)87hy1SUSfcg(%Nw<mvs'
        '$~2uzwH3gEI-tB2^c%V77iPxp@dr^yVAq5?sEfYKn`Uz<tnkkkV7n>D~;YczOCbDP1~@kVC}_wllMyo=9=<;GdX$'
        'Z2P0nrY}f1lkr`Su4JN;eyxp~S_2mEkbSFe8SYcNT!SO{y(DsmC&!H*GCRDtR{Q+1KYxUz(Ze=RG<*F^NS%;m$UK'
        ')|o6Xt`XgY@@nU>!F;_PuE@qljVx^pLOnFPuQZOi3j(9Bl;7f(xS@4oloep1V~NKq)jKJvw$%ff+=hn@$oc$KF0O'
        'nHK!^&_lRYAvv<a46&H<<(g2L4m9jv1Vwi<d!ggdQrS?nE1pqaU@+(=eUe_BV?Sj!cT%a9&F-'
        'JZi+zk=htX4#zd?5IO(?@ClXZrD!jS)|B(ou$*lwVtyun1tu6w23M#m4ErMzuP<F(7>Ef@7<e8ox85?!aRk2XBvN'
        '%_bP$ph_Y;)VAZ08p&3#RI4G~UGHv97^A!=#RUzg9*T94=)NF<td9v+3qz667fv{CU#Nk>_SYD+`{?b)J-'
        'BI(&a7S@RCZkZazkZrCTL&i_r*y~R~ud^P}!v5IQErYXyBH!0j~vMjIbEW=()Hu|1>WH9}(eZ>YYz;YY_``4R)1C'
        'W>=rv'
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
