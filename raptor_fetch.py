#!/usr/bin/env python3
"""
RAPTOR Fetch v2.0 — GitHub Actions
Nuova logica segnali BUY1/BUY2/BUY3/EXIT1/EXIT2
- BUY1: SAR bullish + cross KAMA ≤3 barre + AO in miglioramento (anche sotto zero)
- BUY2: Prezzo > KAMA + Baf ≥ 2
- BUY3: Prezzo > KAMA + ER ≥ 0.50 + Baf ≥ 3 + MM align
- EXIT1: SAR bearish (alleggerisci — anche se prezzo > KAMA)
- EXIT2: Prezzo < KAMA + SAR bearish (esci tutto)
- MEAN REV: ER < 0.30 + RSI < 30 + AO in miglioramento + vicino KAMA
- WATCH: tutto il resto
Trendycator: solo informativo, non blocca segnali
Universe filtrato: esclude BOND, Liquidita, Fineco_OBBLIGAZIONARI
"""

import json, time, datetime, math
import yfinance as yf

def sanitize_nan(obj):
    """Converte ricorsivamente NaN/Infinity in None — NaN non è JSON valido
    e rompe il parsing dell'intero file lato browser (JSON.parse fallisce su tutto)."""
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    if isinstance(obj, dict):
        return {k: sanitize_nan(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_nan(v) for v in obj]
    return obj

# ═══════════════════════════════════════════════════════
#  CATEGORIE DA ESCLUDERE (non analizzate)
# ═══════════════════════════════════════════════════════
CATEGORIE_ESCLUSE = {
    'BOND', 'Liquidità', 'Liquidita', 'Monetario',
    'Fineco_OBBLIGAZIONARI', 'Obbligazionario',
}
PAROLE_ESCLUSE_NOME = [
    'bond','treasury','overnight','government',
    'corporate','inflation-linked',
]

def da_escludere(info):
    cat  = info.get('c','')
    nome = info.get('n','').lower()
    if cat in CATEGORIE_ESCLUSE: return True
    if any(p in nome for p in PAROLE_ESCLUSE_NOME): return True
    return False

# ═══════════════════════════════════════════════════════
#  VIX / VSTOXX — regime di mercato
# ═══════════════════════════════════════════════════════
def fetch_vix_regime():
    vix = None; vstoxx = None
    for sym, key in [('^VIX','vix'),('^V2TX','vstoxx')]:
        try:
            h = yf.Ticker(sym).history(period='5d',interval='1d',timeout=10)
            if not h.empty:
                val = round(float(h['Close'].iloc[-1]),2)
                if key=='vix': vix=val
                else: vstoxx=val
        except: pass
        time.sleep(0.3)
    avg = ((vix or 20) + (vstoxx or 20)) / 2
    if avg < 15:  regime,mult,color = 'CALMA',     1.00,'verde'
    elif avg < 20: regime,mult,color = 'NORMALE',   0.95,'giallo'
    elif avg < 25: regime,mult,color = 'ATTENZIONE',0.85,'arancio'
    elif avg < 30: regime,mult,color = 'STRESS',    0.70,'rosso'
    else:          regime,mult,color = 'PAURA',     0.50,'rosso_scuro'
    return {'vix':vix,'vstoxx':vstoxx,'regime':regime,'mult':mult,'color':color}

# ═══════════════════════════════════════════════════════
#  TICKER LIST
# ═══════════════════════════════════════════════════════
TICKERS_ALL = [{"y":"IAEX.AS","c":"Paesi","t":"IAEX"},{"y":"TOF.AS","c":"ATTIVO","t":"TOF"},{"y":"18MN.DE","c":"Lazy","t":"18MN"},{"y":"7USH.DE","c":"BOND","t":"7USH"},{"y":"CBUH.DE","c":"ATTIVO","t":"CBUH"},{"y":"CEB1.DE","c":"BOND","t":"CEB1"},{"y":"CEB4.DE","c":"NEW AREA","t":"CEB4"},{"y":"GXDW","c":"Paesi","t":"GXDW"},{"y":"DBZB.DE","c":"Lazy","t":"DBZB"},{"y":"EUNY.DE","c":"ATTIVO","t":"EUNY"},{"y":"FTGM.DE","c":"ATTIVO","t":"FTGM"},{"y":"IBC5.DE","c":"BOND","t":"IBC5"},{"y":"IBCJ.DE","c":"Paesi","t":"IBCJ"},{"y":"IQQ9.DE","c":"NEW AREA","t":"IQQ9"},{"y":"IQQF.DE","c":"NEW AREA","t":"IQQF"},{"y":"IS04.DE","c":"BOND","t":"IS04"},{"y":"IS3C.DE","c":"Lazy","t":"IS3C"},{"y":"IS3N.DE","c":"Lazy","t":"IS3N"},{"y":"IS3U.DE","c":"Paesi","t":"IS3U"},{"y":"ISPA.DE","c":"ATTIVO","t":"ISPA"},{"y":"IUSQ.DE","c":"Lazy","t":"IUSQ"},{"y":"IUSS.DE","c":"Paesi","t":"IUSS"},{"y":"LCUJ.DE","c":"Lazy","t":"LCUJ"},{"y":"MJMT.DE","c":"ATTIVO","t":"MJMT"},{"y":"QDVA.DE","c":"ATTIVO","t":"QDVA"},{"y":"SPP5.DE","c":"BOND","t":"SPP5"},{"y":"SPYX.DE","c":"ATTIVO","t":"SPYX"},{"y":"SXR1.DE","c":"Lazy","t":"SXR1"},{"y":"SXRT.DE","c":"Lazy","t":"SXRT"},{"y":"SXRU.DE","c":"NEW AREA","t":"SXRU"},{"y":"SXRW.DE","c":"Lazy","t":"SXRW"},{"y":"VGWE.DE","c":"ATTIVO","t":"VGWE"},{"y":"VUKG.DE","c":"Paesi","t":"VUKG"},{"y":"XBAS.DE","c":"Paesi","t":"XBAS"},{"y":"XCS3.DE","c":"Paesi","t":"XCS3"},{"y":"XCS4.DE","c":"Paesi","t":"XCS4"},{"y":"XD9E.DE","c":"Lazy","t":"XD9E"},{"y":"XD9U.DE","c":"Lazy","t":"XD9U"},{"y":"XDEM.DE","c":"ATTIVO","t":"XDEM"},{"y":"XESD.DE","c":"Paesi","t":"XESD"},{"y":"XGIN.DE","c":"Lazy","t":"XGIN"},{"y":"XMKA.DE","c":"Paesi","t":"XMKA"},{"y":"XPQP.DE","c":"Paesi","t":"XPQP"},{"y":"XWEM.DE","c":"ATTIVO","t":"XWEM"},{"y":"F701.F","c":"ATTIVO","t":"F701"},{"y":"F702.F","c":"ATTIVO","t":"F702"},{"y":"F703.F","c":"ATTIVO","t":"F703"},{"y":"IUSN.F","c":"ADVICE","t":"IUSN"},{"y":"IVAI.MI","c":"Tematici","t":"IVAI"},{"y":"IVDF.DE","c":"Tematici","t":"IVDF"},{"y":"NQSE.F","c":"NEW AREA","t":"NQSE"},{"y":"NTSZ.DE","c":"ATTIVO","t":"NTSZ"},{"y":"IEFM.L","c":"ATTIVO","t":"IEFM"},{"y":"ACT20.MI","c":"ATTIVO","t":"ACT20"},{"y":"ACT60.MI","c":"ATTIVO","t":"ACT60"},{"y":"ACTEQ.MI","c":"ATTIVO","t":"ACTEQ"},{"y":"AGED.MI","c":"Tematici","t":"AGED"},{"y":"AI4UJ.MI","c":"Tematici","t":"AI4UJ"},{"y":"AIAA.MI","c":"Tematici","t":"AIAA"},{"y":"AIAI.MI","c":"Tematici","t":"AIAI"},{"y":"AIGA.MI","c":"Materie","t":"AIGA"},{"y":"AIGC.MI","c":"Materie","t":"AIGC"},{"y":"AIGE.MI","c":"Materie","t":"AIGE"},{"y":"AIGG.MI","c":"Materie","t":"AIGG"},{"y":"AIGI.MI","c":"Materie","t":"AIGI"},{"y":"AIGL.MI","c":"Materie","t":"AIGL"},{"y":"AIGO.MI","c":"Materie","t":"AIGO"},{"y":"AIGP.MI","c":"Materie","t":"AIGP"},{"y":"AIGS.MI","c":"Materie","t":"AIGS"},{"y":"AINF.MI","c":"Tematici","t":"AINF"},{"y":"AIQE.MI","c":"Tematici","t":"AIQE"},{"y":"ALAT.MI","c":"NEW AREA","t":"ALAT"},{"y":"ALUM.MI","c":"Materie","t":"ALUM"},{"y":"ANAU.MI","c":"ADVICE","t":"ANAU"},{"y":"AQWA.MI","c":"Tematici","t":"AQWA"},{"y":"ARMI.MI","c":"Tematici","t":"ARMI"},{"y":"ARMR.MI","c":"Tematici","t":"ARMR"},{"y":"AUCO.MI","c":"Tematici","t":"AUCO"},{"y":"AUHEUA.MI","c":"Paesi","t":"AUHEUA"},{"y":"BATT.MI","c":"Tematici","t":"BATT"},{"y":"BCHN.MI","c":"Settoriali","t":"BCHN"},{"y":"BENE.MI","c":"Materie","t":"BENE"},{"y":"BIODV.MI","c":"Settoriali","t":"BIODV"},{"y":"BIOT.MI","c":"Tematici","t":"BIOT"},{"y":"BKCH.MI","c":"Tematici","t":"BKCH"},{"y":"BLTH.MI","c":"Tematici","t":"BLTH"},{"y":"BNK.MI","c":"Settoriali","t":"BNK"},{"y":"BNKE.MI","c":"Settoriali","t":"BNKE"},{"y":"BOTZ.MI","c":"Tematici","t":"BOTZ"},{"y":"BRENT.MI","c":"Materie","t":"BRENT"},{"y":"BRES.MI","c":"Settoriali","t":"BRES"},{"y":"BRIJ.MI","c":"Tematici","t":"BRIJ"},{"y":"BRND.MI","c":"Materie","t":"BRND"},{"y":"BRNT.MI","c":"Materie","t":"BRNT"},{"y":"BTC.MI","c":"Tematici","t":"BTC"},{"y":"BTECH.MI","c":"Tematici","t":"BTECH"},{"y":"BTECJ.MI","c":"Tematici","t":"BTECJ"},{"y":"BUG.MI","c":"Tematici","t":"BUG"},{"y":"C40.MI","c":"Paesi","t":"C40"},{"y":"CAHEUA.MI","c":"NEW AREA","t":"CAHEUA"},{"y":"CARB.MI","c":"Materie","t":"CARB"},{"y":"CAUT.MI","c":"Tematici","t":"CAUT"},{"y":"CCEUAS.MI","c":"Materie","t":"CCEUAS"},{"y":"CCUSAS.MI","c":"Materie","t":"CCUSAS"},{"y":"CHIP.MI","c":"ADVICE","t":"CHIP"},{"y":"CHM.MI","c":"Settoriali","t":"CHM"},{"y":"CIBR.MI","c":"ADVICE","t":"CIBR"},{"y":"CIT.MI","c":"Tematici","t":"CIT"},{"y":"CITE.MI","c":"Tematici","t":"CITE"},{"y":"CITY.MI","c":"Tematici","t":"CITY"},{"y":"CLOU.MI","c":"Tematici","t":"CLOU"},{"y":"CMOC.MI","c":"Materie","t":"CMOC"},{"y":"CMOD.MI","c":"Materie","t":"CMOD"},{"y":"CMOE.MI","c":"Materie","t":"CMOE"},{"y":"CN1.MI","c":"Paesi","t":"CN1"},{"y":"CO2.MI","c":"Materie","t":"CO2"},{"y":"COCO.MI","c":"Materie","t":"COCO"},{"y":"COFF.MI","c":"Materie","t":"COFF"},{"y":"COMF.MI","c":"Materie","t":"COMF"},{"y":"COMH.MI","c":"Materie","t":"COMH"},{"y":"COMO.MI","c":"Materie","t":"COMO"},{"y":"COPA.MI","c":"Materie","t":"COPA"},{"y":"COPM.MI","c":"Tematici","t":"COPM"},{"y":"COPR.MI","c":"Tematici","t":"COPR"},{"y":"COPX.MI","c":"Tematici","t":"COPX"},{"y":"CORN.MI","c":"Materie","t":"CORN"},{"y":"COTN.MI","c":"Materie","t":"COTN"},{"y":"CROP.MI","c":"Tematici","t":"CROP"},{"y":"CRRY.MI","c":"Materie","t":"CRRY"},{"y":"CRUD.MI","c":"Materie","t":"CRUD"},{"y":"CSCA.MI","c":"NEW AREA","t":"CSCA"},{"y":"CSEMAS.MI","c":"NEW AREA","t":"CSEMAS"},{"y":"CSMIB.MI","c":"Paesi","t":"CSMIB"},{"y":"CSNDX.MI","c":"Paesi","t":"CSNDX"},{"y":"CSPXJ.MI","c":"NEW AREA","t":"CSPXJ"},{"y":"CSSPX.MI","c":"ADVICE","t":"CSSPX"},{"y":"CSUS.MI","c":"ADVICE","t":"CSUS"},{"y":"CSUSS.MI","c":"ADVICE","t":"CSUSS"},{"y":"CTEK.MI","c":"Tematici","t":"CTEK"},{"y":"CURE.MI","c":"Tematici","t":"CURE"},{"y":"CWE.MI","c":"Settoriali","t":"CWE"},{"y":"CYBO.MI","c":"Tematici","t":"CYBO"},{"y":"CYBR.MI","c":"Settoriali","t":"CYBR"},{"y":"DAPP.MI","c":"Tematici","t":"DAPP"},{"y":"DEFS.MI","c":"Settoriali","t":"DEFS"},{"y":"DEMR.MI","c":"ATTIVO","t":"DEMR"},{"y":"DFND.MI","c":"Tematici","t":"DFND"},{"y":"DFNS.MI","c":"Tematici","t":"DFNS"},{"y":"DGTL.MI","c":"Tematici","t":"DGTL"},{"y":"DISW.MI","c":"Settoriali","t":"DISW"},{"y":"DJE.MI","c":"Paesi","t":"DJE"},{"y":"DMAT.MI","c":"Tematici","t":"DMAT"},{"y":"DOCT.MI","c":"Tematici","t":"DOCT"},{"y":"DPAY.MI","c":"Tematici","t":"DPAY"},{"y":"DRVE.MI","c":"Tematici","t":"DRVE"},{"y":"DXJF.MI","c":"ATTIVO","t":"DXJF"},{"y":"EALU.MI","c":"Materie","t":"EALU"},{"y":"EBIZ.MI","c":"Tematici","t":"EBIZ"},{"y":"EBRT.MI","c":"Materie","t":"EBRT"},{"y":"EBUY.MI","c":"Tematici","t":"EBUY"},{"y":"ECAR.MI","c":"Tematici","t":"ECAR"},{"y":"ECEH.MI","c":"Materie","t":"ECEH"},{"y":"ECOF.MI","c":"Materie","t":"ECOF"},{"y":"ECOM.MI","c":"Tematici","t":"ECOM"},{"y":"ECOP.MI","c":"Materie","t":"ECOP"},{"y":"ECRD.MI","c":"Materie","t":"ECRD"},{"y":"ECRN.MI","c":"Materie","t":"ECRN"},{"y":"ECTN.MI","c":"Materie","t":"ECTN"},{"y":"EDOC.MI","c":"Tematici","t":"EDOC"},{"y":"EEA.MI","c":"Tematici","t":"EEA"},{"y":"EEIA.MI","c":"ATTIVO","t":"EEIA"},{"y":"EENG.MI","c":"Settoriali","t":"EENG"},{"y":"EFCM.MI","c":"Materie","t":"EFCM"},{"y":"EGEHE.MI","c":"Settoriali","t":"EGEHE"},{"y":"EIMI.MI","c":"ADVICE","t":"EIMI"},{"y":"EIMT.MI","c":"Materie","t":"EIMT"},{"y":"ELCR.MI","c":"Tematici","t":"ELCR"},{"y":"EMOVE.MI","c":"Tematici","t":"EMOVE"},{"y":"EMOVJ.MI","c":"Tematici","t":"EMOVJ"},{"y":"EMQQ.MI","c":"Settoriali","t":"EMQQ"},{"y":"ENCO.MI","c":"Materie","t":"ENCO"},{"y":"ENERW.MI","c":"Settoriali","t":"ENERW"},{"y":"ENGS.MI","c":"Materie","t":"ENGS"},{"y":"ENIK.MI","c":"Materie","t":"ENIK"},{"y":"ENRG.MI","c":"Settoriali","t":"ENRG"},{"y":"ENTR.MI","c":"Materie","t":"ENTR"},{"y":"EPRA.MI","c":"Tematici","t":"EPRA"},{"y":"EPRE.MI","c":"Tematici","t":"EPRE"},{"y":"EROX.MI","c":"ADVICE","t":"EROX"},{"y":"ESGO.MI","c":"Tematici","t":"ESGO"},{"y":"ESOY.MI","c":"Materie","t":"ESOY"},{"y":"ESPO.MI","c":"Tematici","t":"ESPO"},{"y":"ESPY.MI","c":"Tematici","t":"ESPY"},{"y":"EST.MI","c":"NEW AREA","t":"EST"},{"y":"ESUG.MI","c":"Materie","t":"ESUG"},{"y":"EWAT.MI","c":"Materie","t":"EWAT"},{"y":"EXS1.MI","c":"Paesi","t":"EXS1"},{"y":"EXXY.MI","c":"Materie","t":"EXXY"},{"y":"EZNC.MI","c":"Materie","t":"EZNC"},{"y":"FAMAMW.MI","c":"Tematici","t":"FAMAMW"},{"y":"FAMMAI.MI","c":"Tematici","t":"FAMMAI"},{"y":"FAMMWF.MI","c":"Tematici","t":"FAMMWF"},{"y":"FAMMWS.MI","c":"Tematici","t":"FAMMWS"},{"y":"FAMTEL.MI","c":"Tematici","t":"FAMTEL"},{"y":"FAMWCS.MI","c":"Tematici","t":"FAMWCS"},{"y":"FCRU.MI","c":"Materie","t":"FCRU"},{"y":"FGEA.MI","c":"ATTIVO","t":"FGEA"},{"y":"FINSW.MI","c":"Settoriali","t":"FINSW"},{"y":"FINX.MI","c":"Tematici","t":"FINX"},{"y":"FLXI.MI","c":"Paesi","t":"FLXI"},{"y":"FLXT.MI","c":"Paesi","t":"FLXT"},{"y":"FLXU.MI","c":"Paesi","t":"FLXU"},{"y":"FMI.MI","c":"Paesi","t":"FMI"},{"y":"FOFD.MI","c":"Tematici","t":"FOFD"},{"y":"FOO.MI","c":"Settoriali","t":"FOO"},{"y":"FOOD.MI","c":"Settoriali","t":"FOOD"},{"y":"FUSU.MI","c":"ATTIVO","t":"FUSU"},{"y":"GAS.MI","c":"Materie","t":"GAS"},{"y":"GCLE.MI","c":"Tematici","t":"GCLE"},{"y":"GDIG.MI","c":"Tematici","t":"GDIG"},{"y":"GDX.MI","c":"Tematici","t":"GDX"},{"y":"GDXJ.MI","c":"Tematici","t":"GDXJ"},{"y":"GENDEE.MI","c":"Tematici","t":"GENDEE"},{"y":"GLUG.MI","c":"Tematici","t":"GLUG"},{"y":"GLUX.MI","c":"Tematici","t":"GLUX"},{"y":"GNOM.MI","c":"Tematici","t":"GNOM"},{"y":"GOAI.MI","c":"Tematici","t":"GOAI"},{"y":"GRC.MI","c":"Paesi","t":"GRC"},{"y":"GRCTB.MI","c":"Settoriali","t":"GRCTB"},{"y":"GREAL.MI","c":"Settoriali","t":"GREAL"},{"y":"GSCE.MI","c":"Materie","t":"GSCE"},{"y":"GSM.MI","c":"Tematici","t":"GSM"},{"y":"HDRO.MI","c":"Tematici","t":"HDRO"},{"y":"HEAL.MI","c":"Tematici","t":"HEAL"},{"y":"HERU.MI","c":"Tematici","t":"HERU"},{"y":"HIDIJ.MI","c":"ATTIVO","t":"HIDIJ"},{"y":"HLT.MI","c":"Settoriali","t":"HLT"},{"y":"HLTW.MI","c":"Settoriali","t":"HLTW"},{"y":"HMXJ.MI","c":"ADVICE","t":"HMXJ"},{"y":"HNSC.MI","c":"Tematici","t":"HNSC"},{"y":"HPNA.MI","c":"Settoriali","t":"HPNA"},{"y":"HSTE.MI","c":"Paesi","t":"HSTE"},{"y":"HTWO.MI","c":"Tematici","t":"HTWO"},{"y":"HYDE.MI","c":"Tematici","t":"HYDE"},{"y":"HYGN.MI","c":"Tematici","t":"HYGN"},{"y":"HYLD.MI","c":"ADVICE","t":"HYLD"},{"y":"IAPD.MI","c":"NEW AREA","t":"IAPD"},{"y":"IBZL.MI","c":"Paesi","t":"IBZL"},{"y":"ICBR.MI","c":"Tematici","t":"ICBR"},{"y":"EIMI.MI","c":"ADVICE","t":"EIMI"},{"y":"IEMO.MI","c":"ATTIVO","t":"IEMO"},{"y":"IJPE.MI","c":"NEW AREA","t":"IJPE"},{"y":"IMIB.MI","c":"Paesi","t":"IMIB"},{"y":"INDG.MI","c":"Settoriali","t":"INDG"},{"y":"INDGW.MI","c":"Settoriali","t":"INDGW"},{"y":"INDI.MI","c":"Paesi","t":"INDI"},{"y":"INDO.MI","c":"Paesi","t":"INDO"},{"y":"INQQ.MI","c":"Tematici","t":"INQQ"},{"y":"INS.MI","c":"Settoriali","t":"INS"},{"y":"ISAC.MI","c":"NEW AREA","t":"ISAC"},{"y":"ISAG.MI","c":"Tematici","t":"ISAG"},{"y":"ISPY.MI","c":"Tematici","t":"ISPY"},{"y":"ITBL.MI","c":"Paesi","t":"ITBL"},{"y":"IUSE.MI","c":"NEW AREA","t":"IUSE"},{"y":"IWDE.MI","c":"NEW AREA","t":"IWDE"},{"y":"IWMO.MI","c":"ATTIVO","t":"IWMO"},{"y":"IWVL.MI","c":"ADVICE","t":"IWVL"},{"y":"JEDI.MI","c":"Tematici","t":"JEDI"},{"y":"JRGE.MI","c":"NEW AREA","t":"JRGE"},{"y":"KARS.MI","c":"Settoriali","t":"KARS"},{"y":"KOR.MI","c":"Paesi","t":"KOR"},{"y":"KRBN.MI","c":"Materie","t":"KRBN"},{"y":"KWBE.MI","c":"Tematici","t":"KWBE"},{"y":"LABL.MI","c":"Tematici","t":"LABL"},{"y":"LAFRI.MI","c":"NEW AREA","t":"LAFRI"},{"y":"LCCN.MI","c":"Paesi","t":"LCCN"},{"y":"LEAD.MI","c":"Materie","t":"LEAD"},{"y":"LGUS.MI","c":"Paesi","t":"LGUS"},{"y":"LINXB.MI","c":"ATTIVO","t":"LINXB"},{"y":"LITM.MI","c":"Tematici","t":"LITM"},{"y":"LITU.MI","c":"Tematici","t":"LITU"},{"y":"LOCK.MI","c":"Tematici","t":"LOCK"},{"y":"LTAM.MI","c":"NEW AREA","t":"LTAM"},{"y":"LVO.MI","c":"Materie","t":"LVO"},{"y":"MACV.MI","c":"ATTIVO","t":"MACV"},{"y":"MAGR.MI","c":"ATTIVO","t":"MAGR"},{"y":"MATW.MI","c":"Settoriali","t":"MATW"},{"y":"MCHN.MI","c":"Paesi","t":"MCHN"},{"y":"MCHT.MI","c":"Tematici","t":"MCHT"},{"y":"META.MI","c":"Materie","t":"META"},{"y":"METAA.MI","c":"Tematici","t":"METAA"},{"y":"METAJ.MI","c":"Tematici","t":"METAJ"},{"y":"METE.MI","c":"Tematici","t":"METE"},{"y":"METL.MI","c":"Tematici","t":"METL"},{"y":"MILL.MI","c":"Tematici","t":"MILL"},{"y":"MLPS.MI","c":"Tematici","t":"MLPS"},{"y":"MODR.MI","c":"ATTIVO","t":"MODR"},{"y":"MTAV.MI","c":"Tematici","t":"MTAV"},{"y":"MTVS.MI","c":"Tematici","t":"MTVS"},{"y":"NATO.MI","c":"Settoriali","t":"NATO"},{"y":"NCLR.MI","c":"Tematici","t":"NCLR"},{"y":"NGAS.MI","c":"Materie","t":"NGAS"},{"y":"NICK.MI","c":"Materie","t":"NICK"},{"y":"NRJC.MI","c":"Tematici","t":"NRJC"},{"y":"NTSG.MI","c":"ATTIVO","t":"NTSG"},{"y":"NUCL.MI","c":"Tematici","t":"NUCL"},{"y":"OCEAN.MI","c":"Settoriali","t":"OCEAN"},{"y":"OIH.MI","c":"Tematici","t":"OIH"},{"y":"PAVE.MI","c":"Tematici","t":"PAVE"},{"y":"PCOM.MI","c":"Materie","t":"PCOM"},{"y":"PHAG.MI","c":"Materie","t":"PHAG"},{"y":"PHPD.MI","c":"Materie","t":"PHPD"},{"y":"PHPM.MI","c":"Materie","t":"PHPM"},{"y":"PHPT.MI","c":"Materie","t":"PHPT"},{"y":"QNTM.MI","c":"Tematici","t":"QNTM"},{"y":"QTOP.MI","c":"Paesi","t":"QTOP"},{"y":"QUAD.MI","c":"Tematici","t":"QUAD"},{"y":"RARE.MI","c":"Tematici","t":"RARE"},{"y":"RAYZ.MI","c":"Tematici","t":"RAYZ"},{"y":"RBOT.MI","c":"ADVICE","t":"RBOT"},{"y":"REMX.MI","c":"Tematici","t":"REMX"},{"y":"RENW.MI","c":"Tematici","t":"RENW"},{"y":"REUS.MI","c":"Tematici","t":"REUS"},{"y":"REUSE.MI","c":"Settoriali","t":"REUSE"},{"y":"RNRG.MI","c":"Tematici","t":"RNRG"},{"y":"ROBO.MI","c":"Tematici","t":"ROBO"},{"y":"ROE.MI","c":"Tematici","t":"ROE"},{"y":"SAUDI.MI","c":"Paesi","t":"SAUDI"},{"y":"SAUS.MI","c":"Paesi","t":"SAUS"},{"y":"SBIO.MI","c":"Settoriali","t":"SBIO"},{"y":"SCITY.MI","c":"Tematici","t":"SCITY"},{"y":"SDG9.MI","c":"Tematici","t":"SDG9"},{"y":"SEMA.MI","c":"NEW AREA","t":"SEMA"},{"y":"SEME.MI","c":"Tematici","t":"SEME"},{"y":"SGBS.MI","c":"Materie","t":"SGBS"},{"y":"SILV.MI","c":"Tematici","t":"SILV"},{"y":"SJPA.MI","c":"NEW AREA","t":"SJPA"},{"y":"SMCX.MI","c":"ADVICE","t":"SMCX"},{"y":"SMEA.MI","c":"ADVICE","t":"SMEA"},{"y":"SMH.MI","c":"Tematici","t":"SMH"},{"y":"SNSR.MI","c":"Tematici","t":"SNSR"},{"y":"SOLR.MI","c":"Tematici","t":"SOLR"},{"y":"SOYB.MI","c":"Materie","t":"SOYB"},{"y":"SOYO.MI","c":"Materie","t":"SOYO"},{"y":"SP1E.MI","c":"Paesi","t":"SP1E"},{"y":"SP5A.MI","c":"ADVICE","t":"SP5A"},{"y":"SPXE.MI","c":"Paesi","t":"SPXE"},{"y":"SPXJ.MI","c":"Paesi","t":"SPXJ"},{"y":"SPY5.MI","c":"Paesi","t":"SPY5"},{"y":"SRSA.MI","c":"Paesi","t":"SRSA"},{"y":"STAW.MI","c":"Settoriali","t":"STAW"},{"y":"DFSV.DE","c":"SPDR EURO","t":"DFSV"},{"y":"STKX.MI","c":"SPDR EURO","t":"STKX"},{"y":"STNX.MI","c":"SPDR EURO","t":"STNX"},{"y":"STPX.MI","c":"SPDR EURO","t":"STPX"},{"y":"STQX.MI","c":"SPDR EURO","t":"STQX"},{"y":"STRX.MI","c":"SPDR EURO","t":"STRX"},{"y":"STSX.MI","c":"SPDR EURO","t":"STSX"},{"y":"STTX.MI","c":"SPDR EURO","t":"STTX"},{"y":"STUX.MI","c":"SPDR EURO","t":"STUX"},{"y":"SUGA.MI","c":"Materie","t":"SUGA"},{"y":"SW2CHB.MI","c":"Paesi","t":"SW2CHB"},{"y":"SWDA.MI","c":"ADVICE","t":"SWDA"},{"y":"SXLB.MI","c":"SPDR USA","t":"SXLB"},{"y":"SXLC.MI","c":"SPDR USA","t":"SXLC"},{"y":"SXLF.MI","c":"SPDR USA","t":"SXLF"},{"y":"SXLI.MI","c":"SPDR USA","t":"SXLI"},{"y":"SXLK.MI","c":"SPDR USA","t":"SXLK"},{"y":"SXLP.MI","c":"SPDR USA","t":"SXLP"},{"y":"SXLU.MI","c":"SPDR USA","t":"SXLU"},{"y":"SXLV.MI","c":"SPDR USA","t":"SXLV"},{"y":"SXLY.MI","c":"SPDR USA","t":"SXLY"},{"y":"TELE.MI","c":"Settoriali","t":"TELE"},{"y":"TELEW.MI","c":"Settoriali","t":"TELEW"},{"y":"TLCO.MI","c":"Tematici","t":"TLCO"},{"y":"TNO.MI","c":"Settoriali","t":"TNO"},{"y":"TNOW.MI","c":"Settoriali","t":"TNOW"},{"y":"TRVL.MI","c":"Settoriali","t":"TRVL"},{"y":"TTFW.MI","c":"Materie","t":"TTFW"},{"y":"TUR.MI","c":"Paesi","t":"TUR"},{"y":"U3O8.MI","c":"Tematici","t":"U3O8"},{"y":"UGAS.MI","c":"Materie","t":"UGAS"},{"y":"UKE.MI","c":"Paesi","t":"UKE"},{"y":"UNIC.MI","c":"Tematici","t":"UNIC"},{"y":"URNJ.MI","c":"Tematici","t":"URNJ"},{"y":"URNU.MI","c":"ADVICE","t":"URNU"},{"y":"USTEC.MI","c":"Tematici","t":"USTEC"},{"y":"UTI.MI","c":"Settoriali","t":"UTI"},{"y":"UTIW.MI","c":"Settoriali","t":"UTIW"},{"y":"VEGI.MI","c":"Tematici","t":"VEGI"},{"y":"VITA.MI","c":"Settoriali","t":"VITA"},{"y":"VITU.MI","c":"Settoriali","t":"VITU"},{"y":"VJPE.MI","c":"Paesi","t":"VJPE"},{"y":"VNGA20.MI","c":"ATTIVO","t":"VNGA20"},{"y":"VNGA40.MI","c":"ATTIVO","t":"VNGA40"},{"y":"VNGA60.MI","c":"ATTIVO","t":"VNGA60"},{"y":"VNGA80.MI","c":"ATTIVO","t":"VNGA80"},{"y":"VOLT.MI","c":"Tematici","t":"VOLT"},{"y":"VPN.MI","c":"Tematici","t":"VPN"},{"y":"VUKE.MI","c":"Paesi","t":"VUKE"},{"y":"VUSA.MI","c":"Paesi","t":"VUSA"},{"y":"WATC.MI","c":"Tematici","t":"WATC"},{"y":"WATT.MI","c":"Materie","t":"WATT"},{"y":"WBLK.MI","c":"Tematici","t":"WBLK"},{"y":"WCBR.MI","c":"Tematici","t":"WCBR"},{"y":"WCCA.MI","c":"Materie","t":"WCCA"},{"y":"WCLD.MI","c":"Settoriali","t":"WCLD"},{"y":"WCOA.MI","c":"Materie","t":"WCOA"},{"y":"WCOD.MI","c":"SPDR WORLD","t":"WCOD"},{"y":"WCOE.MI","c":"Materie","t":"WCOE"},{"y":"WCOS.MI","c":"SPDR WORLD","t":"WCOS"},{"y":"WDEF.MI","c":"Tematici","t":"WDEF"},{"y":"WDNA.MI","c":"Tematici","t":"WDNA"},{"y":"WEAT.MI","c":"Materie","t":"WEAT"},{"y":"WEB3.MI","c":"Tematici","t":"WEB3"},{"y":"WENT.MI","c":"Materie","t":"WENT"},{"y":"WENU.MI","c":"Materie","t":"WENU"},{"y":"WFIN.MI","c":"SPDR WORLD","t":"WFIN"},{"y":"WGRO.MI","c":"Tematici","t":"WGRO"},{"y":"WHEA.MI","c":"SPDR WORLD","t":"WHEA"},{"y":"WIND.MI","c":"SPDR WORLD","t":"WIND"},{"y":"WMAT.MI","c":"SPDR WORLD","t":"WMAT"},{"y":"WMGT.MI","c":"Tematici","t":"WMGT"},{"y":"WMIB.MI","c":"Paesi","t":"WMIB"},{"y":"WNAS.MI","c":"Paesi","t":"WNAS"},{"y":"WNDE.MI","c":"Tematici","t":"WNDE"},{"y":"WNDY.MI","c":"Tematici","t":"WNDY"},{"y":"WNRG.MI","c":"SPDR WORLD","t":"WNRG"},{"y":"WRNW.MI","c":"Tematici","t":"WRNW"},{"y":"WRTY.MI","c":"Paesi","t":"WRTY"},{"y":"WS5X.MI","c":"Paesi","t":"WS5X"},{"y":"WSLV.MI","c":"Tematici","t":"WSLV"},{"y":"WSPE.MI","c":"Paesi","t":"WSPE"},{"y":"WSPX.MI","c":"Paesi","t":"WSPX"},{"y":"WTAI.MI","c":"Tematici","t":"WTAI"},{"y":"WTEC.MI","c":"SPDR WORLD","t":"WTEC"},{"y":"WTEL.MI","c":"SPDR WORLD","t":"WTEL"},{"y":"WTI.MI","c":"Materie","t":"WTI"},{"y":"WTID.MI","c":"Materie","t":"WTID"},{"y":"WTRE.MI","c":"Tematici","t":"WTRE"},{"y":"WUTI.MI","c":"SPDR WORLD","t":"WUTI"},{"y":"XAGZ.MI","c":"Materie","t":"XAGZ"},{"y":"XAIX.MI","c":"ADVICE","t":"XAIX"},{"y":"XCHA.MI","c":"Paesi","t":"XCHA"},{"y":"XCS5.MI","c":"Paesi","t":"XCS5"},{"y":"XCTE.MI","c":"Tematici","t":"XCTE"},{"y":"XDAX.MI","c":"Paesi","t":"XDAX"},{"y":"XDBC.MI","c":"Materie","t":"XDBC"},{"y":"XDEE.MI","c":"NEW AREA","t":"XDEE"},{"y":"XDER.MI","c":"Tematici","t":"XDER"},{"y":"XDEV.MI","c":"ADVICE","t":"XDEV"},{"y":"XDG3.MI","c":"Tematici","t":"XDG3"},{"y":"XDG6.MI","c":"Tematici","t":"XDG6"},{"y":"XDG7.MI","c":"Tematici","t":"XDG7"},{"y":"XDGI.MI","c":"Tematici","t":"XDGI"},{"y":"XDRE.MI","c":"Settoriali","t":"XDRE"},{"y":"XDW0.MI","c":"Settoriali","t":"XDW0"},{"y":"XDWC.MI","c":"Settoriali","t":"XDWC"},{"y":"XDWF.MI","c":"Settoriali","t":"XDWF"},{"y":"XDWH.MI","c":"Settoriali","t":"XDWH"},{"y":"XDWI.MI","c":"Settoriali","t":"XDWI"},{"y":"XDWM.MI","c":"Settoriali","t":"XDWM"},{"y":"XDWS.MI","c":"Settoriali","t":"XDWS"},{"y":"XDWT.MI","c":"Settoriali","t":"XDWT"},{"y":"XDWU.MI","c":"Settoriali","t":"XDWU"},{"y":"XFNT.MI","c":"Tematici","t":"XFNT"},{"y":"XFVT.MI","c":"Paesi","t":"XFVT"},{"y":"XG11.MI","c":"Tematici","t":"XG11"},{"y":"XG12.MI","c":"Tematici","t":"XG12"},{"y":"XGEN.MI","c":"Tematici","t":"XGEN"},{"y":"XIFE.MI","c":"Settoriali","t":"XIFE"},{"y":"XLBS.MI","c":"Settoriali","t":"XLBS"},{"y":"XLCS.MI","c":"Settoriali","t":"XLCS"},{"y":"XLES.MI","c":"Settoriali","t":"XLES"},{"y":"XLFS.MI","c":"Settoriali","t":"XLFS"},{"y":"XLIS.MI","c":"Settoriali","t":"XLIS"},{"y":"XLKS.MI","c":"Settoriali","t":"XLKS"},{"y":"XLPE.MI","c":"Tematici","t":"XLPE"},{"y":"XLPS.MI","c":"Settoriali","t":"XLPS"},{"y":"XLUS.MI","c":"Settoriali","t":"XLUS"},{"y":"XLVS.MI","c":"Settoriali","t":"XLVS"},{"y":"XLYS.MI","c":"Settoriali","t":"XLYS"},{"y":"D5BI.DE","c":"Paesi","t":"D5BI"},{"y":"XMME.MI","c":"ADVICE","t":"XMME"},{"y":"XMOV.MI","c":"Tematici","t":"XMOV"},{"y":"XNGI.MI","c":"Tematici","t":"XNGI"},{"y":"XNNV.MI","c":"Tematici","t":"XNNV"},{"y":"XQUI.MI","c":"ATTIVO","t":"XQUI"},{"y":"XRES.MI","c":"Tematici","t":"XRES"},{"y":"XS8R.MI","c":"Tematici","t":"XS8R"},{"y":"XSFR.MI","c":"Paesi","t":"XSFR"},{"y":"XSGI.MI","c":"Tematici","t":"XSGI"},{"y":"XSMI.MI","c":"Paesi","t":"XSMI"},{"y":"XSX6.MI","c":"ADVICE","t":"XSX6"},{"y":"XUSA.MI","c":"ATTIVO","t":"XUSA"},{"y":"XUTC.MI","c":"Settoriali","t":"XUTC"},{"y":"XWTS.MI","c":"Settoriali","t":"XWTS"},{"y":"XXSC.MI","c":"ATTIVO","t":"XXSC"},{"y":"ZINC.MI","c":"Materie","t":"ZINC"},{"y":"EIDO","c":"Paesi","t":"EIDO"},{"y":"EIRL","c":"Paesi","t":"EIRL"},{"y":"IMOM","c":"ATTIVO","t":"IMOM"},{"y":"DBMFE.PA","c":"ATTIVO","t":"DBMFE"},{"y":"MEUD.PA","c":"NEW AREA","t":"MEUD"},{"y":"WRD.PA","c":"Paesi","t":"WRD"},{"y":"SXLE.MI","c":"SPDR USA","t":"SXLE"},{"y":"MGIN.MI","c":"SPDR USA","t":"MGIN"},{"y":"STWX.MI","c":"SPDR EURO","t":"STWX"},{"y":"STZX.MI","c":"SPDR EURO","t":"STZX"},{"y":"SWRD.MI","c":"benchmark","t":"SWRD"},{"y":"600X.MI","c":"benchmark","t":"600X"},{"y":"EIS","c":"Paesi","t":"EIS"},{"y":"ENZL","c":"Paesi","t":"ENZL"},{"y":"EPHE","c":"Paesi","t":"EPHE"},{"y":"EPI","c":"Paesi","t":"EPI"},{"y":"EPOL","c":"Paesi","t":"EPOL"},{"y":"EPU","c":"Paesi","t":"EPU"},{"y":"EWA","c":"Paesi","t":"EWA"},{"y":"EWC","c":"Paesi","t":"EWC"},{"y":"EWD","c":"Paesi","t":"EWD"},{"y":"EWG","c":"Paesi","t":"EWG"},{"y":"EWH","c":"Paesi","t":"EWH"},{"y":"EWI","c":"Paesi","t":"EWI"},{"y":"EWJ","c":"Paesi","t":"EWJ"},{"y":"EWK","c":"Paesi","t":"EWK"},{"y":"EWL","c":"Paesi","t":"EWL"},{"y":"EWM","c":"Paesi","t":"EWM"},{"y":"EWN","c":"Paesi","t":"EWN"},{"y":"EWO","c":"Paesi","t":"EWO"},{"y":"EWP","c":"Paesi","t":"EWP"},{"y":"EWQ","c":"Paesi","t":"EWQ"},{"y":"EWS","c":"Paesi","t":"EWS"},{"y":"EWT","c":"Paesi","t":"EWT"},{"y":"EWU","c":"Paesi","t":"EWU"},{"y":"EWW","c":"Paesi","t":"EWW"},{"y":"EWY","c":"Paesi","t":"EWY"},{"y":"EWZ","c":"Paesi","t":"EWZ"},{"y":"EZA","c":"Paesi","t":"EZA"},{"y":"FM.TO","c":"Paesi","t":"FM"},{"y":"GREK","c":"Paesi","t":"GREK"},{"y":"GXG","c":"Paesi","t":"GXG"},{"y":"ICLN","c":"Tematici","t":"ICLN"},{"y":"ILF","c":"Paesi","t":"ILF"},{"y":"MES","c":"Paesi","t":"MES"},{"y":"NORW","c":"Paesi","t":"NORW"},{"y":"QQQ","c":"Paesi","t":"QQQ"},{"y":"SPLV","c":"Paesi","t":"SPLV"},{"y":"SPY","c":"Paesi","t":"SPY"},{"y":"THD","c":"Paesi","t":"THD"},{"y":"UAE","c":"Paesi","t":"UAE"},{"y":"VNM","c":"Paesi","t":"VNM"},{"y":"VPL","c":"Paesi","t":"VPL"},{"y":"ADS.DE","c":"EUROGROW","t":"ADS"},{"y":"ADYEN.AS","c":"EUROGROW","t":"ADYEN"},{"y":"AI.PA","c":"EUROGROW","t":"AI"},{"y":"AIR.PA","c":"EUROGROW","t":"AIR"},{"y":"AM.PA","c":"EUROGROW","t":"AM"},{"y":"ARGX","c":"EUROGROW","t":"ARGX"},{"y":"ASML.SW","c":"EUROGROW","t":"ASML"},{"y":"BEI.DE","c":"EUROGROW","t":"BEI"},{"y":"CBK.DE","c":"EUROGROW","t":"CBK"},{"y":"DB1.DE","c":"EUROGROW","t":"DB1"},{"y":"DSY.PA","c":"EUROGROW","t":"DSY"},{"y":"DTE.DE","c":"EUROGROW","t":"DTE"},{"y":"EL.PA","c":"EUROGROW","t":"EL"},{"y":"ENR.DE","c":"EUROGROW","t":"ENR"},{"y":"FER.MC","c":"EUROGROW","t":"FER"},{"y":"HEI.DE","c":"EUROGROW","t":"HEI"},{"y":"HO.PA","c":"EUROGROW","t":"HO"},{"y":"IFX.DE","c":"EUROGROW","t":"IFX"},{"y":"KNEBV.HE","c":"EUROGROW","t":"KNEBV"},{"y":"LDO.MI","c":"EUROGROW","t":"LDO"},{"y":"LR.PA","c":"EUROGROW","t":"LR"},{"y":"MC.PA","c":"EUROGROW","t":"MC"},{"y":"NOKIA.HE","c":"EUROGROW","t":"NOKIA"},{"y":"OR.PA","c":"EUROGROW","t":"OR"},{"y":"PRX.AS","c":"EUROGROW","t":"PRX"},{"y":"PRY.MI","c":"EUROGROW","t":"PRY"},{"y":"RACE.MI","c":"EUROGROW","t":"RACE"},{"y":"RHM.DE","c":"EUROGROW","t":"RHM"},{"y":"RMS.PA","c":"EUROGROW","t":"RMS"},{"y":"RYA.IR","c":"EUROGROW","t":"RYA"},{"y":"SAF.PA","c":"EUROGROW","t":"SAF"},{"y":"SAP.DE","c":"EUROGROW","t":"SAP"},{"y":"SHL.DE","c":"EUROGROW","t":"SHL"},{"y":"SIE.DE","c":"EUROGROW","t":"SIE"},{"y":"SRT.DE","c":"EUROGROW","t":"SRT"},{"y":"SU.PA","c":"EUROGROW","t":"SU"},{"y":"UCG.MI","c":"EUROGROW","t":"UCG"},{"y":"UMG.AS","c":"EUROGROW","t":"UMG"},{"y":"swda.MI","c":"benchmark","t":"SWDA_B"},{"y":"xdwd.MI","c":"benchmark","t":"XDWD"},{"y":"cw8.MI","c":"benchmark","t":"CW8"},{"y":"imeu.MI","c":"benchmark","t":"IMEU"},{"y":"inaa.MI","c":"benchmark","t":"INAA"}]

# Filtra i ticker da analizzare
TICKERS = [t for t in TICKERS_ALL if not da_escludere(t)]

# ═══════════════════════════════════════════════════════
#  INDICATORI
# ═══════════════════════════════════════════════════════
def calc_kama(close, n=10, fast=2, slow=30):
    fast_sc = 2/(fast+1)
    slow_sc = 2/(slow+1)
    kama = [None]*len(close)
    if len(close) <= n: return kama
    kama[n] = close[n]
    for i in range(n+1, len(close)):
        direction  = abs(close[i] - close[i-n])
        volatility = sum(abs(close[j] - close[j-1]) for j in range(i-n+1, i+1))
        er  = direction/volatility if volatility != 0 else 0
        sc  = (er*(fast_sc - slow_sc) + slow_sc)**2
        kama[i] = kama[i-1] + sc*(close[i] - kama[i-1])
    return kama

def calc_er(close, n=10):
    if len(close) < n+1: return 0
    direction  = abs(close[-1] - close[-n-1])
    volatility = sum(abs(close[-i] - close[-i-1]) for i in range(1, n+1))
    return round(direction/volatility, 4) if volatility != 0 else 0

def calc_rsi(close, n=14):
    if len(close) < n+2: return 50
    gains, losses = [], []
    for i in range(1, len(close)):
        d = close[i] - close[i-1]
        gains.append(max(d,0))
        losses.append(max(-d,0))
    avg_g = sum(gains[-n:])/n
    avg_l = sum(losses[-n:])/n
    if avg_l == 0: return 100
    return round(100 - 100/(1+avg_g/avg_l), 2)

def calc_ao_array(high, low):
    """Calcola AO come array — serve per AO improving"""
    mid = [(h+l)/2 for h,l in zip(high,low)]
    result = [None]*len(mid)
    for i in range(33, len(mid)):
        sma5  = sum(mid[i-4:i+1])/5
        sma34 = sum(mid[i-33:i+1])/34
        result[i] = round(sma5 - sma34, 4)
    return result

def calc_ao(high, low):
    """AO scalare ultimo valore"""
    arr = calc_ao_array(high, low)
    for v in reversed(arr):
        if v is not None: return v
    return 0

def calc_ao_improving(high, low):
    """AO barra corrente > barra precedente (anche sotto zero)"""
    arr = [v for v in calc_ao_array(high, low) if v is not None]
    if len(arr) < 2: return False
    return arr[-1] > arr[-2]

def calc_baffetti(high, low):
    if len(high) < 3: return 0
    mid = [(h+l)/2 for h,l in zip(high,low)]
    count = 0
    for i in range(len(mid)-1, 0, -1):
        if mid[i] > mid[i-1]: count += 1
        else: break
    return count

def calc_sar(high, low, af0=0.02, af_max=0.20):
    """Parabolic SAR — restituisce (sar_value, is_bullish, flip_idx)
    flip_idx = indice della barra in cui è avvenuto l'ultimo cambio bull/bear"""
    if len(high) < 5: return None, True, 0
    sar   = low[0]
    ep    = high[0]
    af    = af0
    bull  = True
    flip_idx = 0
    for i in range(1, len(high)):
        if bull:
            new_sar = sar + af*(ep - sar)
            new_sar = min(new_sar, low[max(0,i-1)], low[max(0,i-2)])
            if low[i] < new_sar:
                bull = False; new_sar = ep; ep = low[i]; af = af0; flip_idx = i
            else:
                if high[i] > ep:
                    ep = high[i]; af = min(af+af0, af_max)
        else:
            new_sar = sar + af*(ep - sar)
            new_sar = max(new_sar, high[max(0,i-1)], high[max(0,i-2)])
            if high[i] > new_sar:
                bull = True; new_sar = ep; ep = high[i]; af = af0; flip_idx = i
            else:
                if low[i] < ep:
                    ep = low[i]; af = min(af+af0, af_max)
        sar = new_sar
    return round(sar, 4), bull, flip_idx

def calc_trendycator(close):
    """Solo informativo — non blocca segnali"""
    if len(close) < 55: return 'GRIGIO'
    def ema(arr, p):
        k = 2/(p+1); e = arr[0]
        for x in arr[1:]: e = x*k + e*(1-k)
        return e
    e21 = ema(close, 21)
    e55 = ema(close, 55)
    if e21 > e55: return 'VERDE'
    if e21 < e55: return 'ROSSO'
    return 'GRIGIO'

def calc_vol_ratio(volume):
    if len(volume) < 21: return 1.0
    avg20 = sum(volume[-21:-1])/20
    return round(volume[-1]/avg20, 2) if avg20 > 0 else 1.0

def calc_perf(close, days):
    if len(close) <= days: return 0
    ref = close[-days-1]
    return round((close[-1]/ref - 1)*100, 2) if ref > 0 else 0

def calc_mm_align(close):
    if len(close) < 100: return False
    mm20  = sum(close[-20:])/20
    mm50  = sum(close[-50:])/50
    mm100 = sum(close[-100:])/100
    return close[-1] > mm20 > mm50 > mm100

def calc_cross_days(close, kama):
    valid = [(c,k) for c,k in zip(close,kama) if k is not None]
    if len(valid) < 2: return 999
    above_now = valid[-1][0] > valid[-1][1]
    for i in range(len(valid)-2, -1, -1):
        if (valid[i][0] > valid[i][1]) != above_now:
            return len(valid)-1 - i
    return 999

def calc_entry_date(close, kama, timestamps):
    valid = [(c,k,t) for c,k,t in zip(close,kama,timestamps) if k is not None]
    if len(valid) < 2: return '—'
    above_now = valid[-1][0] > valid[-1][1]
    for i in range(len(valid)-2, -1, -1):
        if (valid[i][0] > valid[i][1]) != above_now:
            dt = datetime.datetime.fromtimestamp(valid[i+1][2])
            return dt.strftime('%d/%m/%Y')
    return '—'

# ═══════════════════════════════════════════════════════
#  CALCOLA SEGNALE — nuova logica v2.0
# ═══════════════════════════════════════════════════════
def calc_segnale(close, high, low, kama, er, baff, ao_improving, sar_bull, cross, mm_align, rsi):
    lk = kama[-1]
    lc = close[-1]
    above_kama = lc > lk if lk else False

    # ── BUY1: SAR bullish + cross KAMA ≤3 barre + AO improving ──
    if sar_bull and cross <= 3 and ao_improving:
        return 'BUY1'

    # ── BUY2: Prezzo > KAMA + Baf ≥ 2 ───────────────────────────
    if above_kama and baff >= 2:
        return 'BUY2'

    # ── BUY3: Prezzo > KAMA + ER ≥ 0.50 + Baf ≥ 3 + MM align ───
    if above_kama and er >= 0.50 and baff >= 3 and mm_align:
        return 'BUY3'

    # ── EXIT2: Prezzo < KAMA + SAR bearish (esci tutto) ──────────
    if not above_kama and not sar_bull:
        return 'EXIT2'

    # ── EXIT1: SAR bearish (alleggerisci) ────────────────────────
    if not sar_bull:
        return 'EXIT1'

    # ── MEAN REV ─────────────────────────────────────────────────
    near_kama = abs(lc-lk)/lk < 0.03 if lk and lk > 0 else False
    if er < 0.30 and rsi < 30 and ao_improving and (near_kama or not above_kama):
        return 'MEAN REV'

    return 'WATCH'

# ═══════════════════════════════════════════════════════
#  SCORE v2.0
# ═══════════════════════════════════════════════════════
def calc_score(segnale, er, baff, pk_pct, perf_s, perf_m, mm_align, ao_pos, cross, regime_mult):
    base = (er*30 + min(baff,10)*5 + min(abs(pk_pct),5)*3
          + max(-10,min(5,perf_s))*4 + max(-20,min(10,perf_m))*2
          + (10 if mm_align else 0) + (5 if ao_pos else 0)
          + (20 if cross<=3 else 12 if cross<=10 else 5 if cross<=20 else 0))
    # Bonus per BUY1 (segnale precoce tempestivo)
    if segnale == 'BUY1': base += 15
    # Penalità per EXIT
    if segnale in ('EXIT1','EXIT2'): base *= 0.5
    return round(base * regime_mult, 1)

# ═══════════════════════════════════════════════════════
#  PROCESS TICKER
# ═══════════════════════════════════════════════════════
def process_ticker(info, regime_mult=1.0):
    symbol = info['y']
    try:
        tk   = yf.Ticker(symbol)
        hist = tk.history(period='1y', interval='1d', timeout=15)
        if hist.empty or len(hist) < 60:
            return None

        nome = info.get('n','')
        if not nome:
            try:
                meta = tk.fast_info
                nome = getattr(meta,'long_name','') or getattr(meta,'short_name','') or ''
                if not nome:
                    inf  = tk.info
                    nome = inf.get('longName','') or inf.get('shortName','') or ''
                nome = nome[:60]
            except:
                nome = ''

        close      = [float(x) for x in hist['Close'].values]
        high       = [float(x) for x in hist['High'].values]
        low        = [float(x) for x in hist['Low'].values]
        volume     = [float(x) for x in hist['Volume'].values]
        timestamps = [int(t.timestamp()) for t in hist.index]

        kama        = calc_kama(close)
        er          = calc_er(close)
        rsi         = calc_rsi(close)
        ao          = calc_ao(high, low)
        ao_improving= calc_ao_improving(high, low)
        baff        = calc_baffetti(high, low)
        trd         = calc_trendycator(close)   # solo informativo
        cross       = calc_cross_days(close, kama)
        vr          = calc_vol_ratio(volume)
        ed          = calc_entry_date(close, kama, timestamps)
        mm_align    = calc_mm_align(close)
        sar_val, sar_bull, sar_flip_idx = calc_sar(high, low)
        sar_date   = datetime.datetime.fromtimestamp(timestamps[sar_flip_idx]).strftime('%d/%m/%Y')
        sar_streak = len(high) - sar_flip_idx

        lk         = kama[-1]
        lc         = close[-1]
        above_kama = lc > lk if lk else False
        ao_pos     = ao > 0
        pk_pct     = round((lc/lk - 1)*100, 2) if lk and lk > 0 else 0
        perf_s     = calc_perf(close, 5)
        perf_m     = calc_perf(close, 20)
        perf_o     = calc_perf(close, 1)

        segnale = calc_segnale(close, high, low, kama, er, baff,
                               ao_improving, sar_bull, cross, mm_align, rsi)
        score   = calc_score(segnale, er, baff, pk_pct, perf_s, perf_m,
                             mm_align, ao_pos, cross, regime_mult)

        return {
            'ticker':      info['t'],
            'yahoo':       symbol,
            'categoria':   info['c'],
            'nome':        nome,
            'segnale':     segnale,
            'score':       score,
            'trendycator': trd,        # solo informativo
            'prezzo':      round(lc, 4),
            'kama':        round(lk, 4) if lk else None,
            'sar':         sar_val,
            'sarBull':     sar_bull,
            'sarDate':     sar_date,
            'sarStreak':   sar_streak,
            'er':          er,
            'baff':        baff,
            'aoImproving': ao_improving,
            'kpct':        pk_pct,
            'ao':          round(ao, 4),
            'rsi':         rsi,
            'perfOggi':    perf_o,
            'perfSett':    perf_s,
            'perfMese':    perf_m,
            'volRatio':    vr,
            'crossDays':   cross,
            'entryDate':   ed,
            'mmAlign':     mm_align,
        }
    except Exception:
        return None

# ═══════════════════════════════════════════════════════
#  EMAIL ALERT v2.0
# ═══════════════════════════════════════════════════════
def send_alert_email(alerts, vix, vstoxx, regime, now, prev_regime=None):
    import smtplib, os
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    EMAIL_USER = os.environ.get('EMAIL_USER','')
    EMAIL_PASS = os.environ.get('EMAIL_PASS','')
    if not EMAIL_USER or not EMAIL_PASS:
        print("EMAIL non configurata — skip")
        return

    regime_changed = prev_regime and prev_regime != regime
    subj = ("⚠️ REGIME {} → {} · {} segnali · {}" if regime_changed else
            "🦅 RAPTOR ONE v2 — {} segnale/i · {}").format(
        *(prev_regime, regime, len(alerts), now.strftime('%d/%m/%Y %H:%M'))
        if regime_changed else (len(alerts), now.strftime('%d/%m/%Y %H:%M')))

    ICONS = {
        'BUY1':'🟢 BUY1','BUY2':'🔵 BUY2','BUY3':'💎 BUY3',
        'EXIT1':'🟡 EXIT1','EXIT2':'🔴 EXIT2',
        'MEAN REV':'🟠 MR','WATCH':'⚪ WATCH',
    }
    BG = {
        'BUY1':'#dafbe1','BUY2':'#ddf4ff','BUY3':'#e8f5e9',
        'EXIT1':'#fff8c5','EXIT2':'#ffebe9',
        'MEAN REV':'#fff1e5','WATCH':'#f5f7fa',
    }

    rows = ''
    for a in alerts:
        bg = BG.get(a['new'],'#ffffff')
        rows += ('<tr style="background:{}">'
            '<td style="padding:6px;font-weight:700;font-family:monospace">{}</td>'
            '<td style="padding:6px;font-size:10px;color:#57606a">{}</td>'
            '<td style="padding:6px;font-size:10px;color:#57606a">{}</td>'
            '<td style="padding:6px">{}</td>'
            '<td style="padding:6px">→</td>'
            '<td style="padding:6px;font-weight:700">{}</td>'
            '<td style="padding:6px;font-family:monospace">{}</td>'
            '<td style="padding:6px;font-weight:700">{}</td>'
            '<td style="padding:6px;font-size:10px;color:#57606a">{}</td>'
            '</tr>').format(
            bg, a['ticker'], a.get('categoria',''), (a['nome'] or '')[:40],
            ICONS.get(a['old'], a['old']), ICONS.get(a['new'], a['new']),
            a['prezzo'], a['score'], a['entry'])

    vix_c  = '#1a7f37' if (vix or 20)<20 else '#bc4c00' if (vix or 20)<28 else '#cf222e'
    banner = ''
    if regime_changed:
        R = {'CALMA':'🟢','NORMALE':'🟡','ATTENZIONE':'🟠','STRESS':'🔴','PAURA':'⛔'}
        banner = ('<div style="background:#1e3a5f;border:2px solid #f59e0b;border-radius:8px;'
                  'padding:10px 16px;margin-bottom:14px">'
                  '<b style="color:#f59e0b">⚠️ CAMBIO REGIME VIX</b>&nbsp;&nbsp;'
                  '{} {} → {} <b>{}</b></div>').format(
                  R.get(prev_regime,''), prev_regime, R.get(regime,''), regime)

    html = '''<!DOCTYPE html><html><body style="font-family:'Segoe UI',sans-serif;background:#f5f7fa;padding:20px">
<div style="max-width:900px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.1)">
  <div style="background:#1f2328;color:#fff;padding:14px 20px">
    <h2 style="margin:0;font-size:18px">🦅 RAPTOR ONE v2 — Nuovi Segnali</h2>
    <p style="margin:4px 0 0;font-size:12px;opacity:.8">{ts} · Regime: <b>{reg}</b> · VIX: <span style="color:{vc};font-weight:700">{vx}</span> / VSTOXX: {vs}</p>
    <p style="margin:2px 0 0;font-size:11px;opacity:.6">BUY1=SAR+CrossKAMA+AO · BUY2=KAMA+Baf≥2 · BUY3=KAMA+ER≥0.5+Baf≥3+MM · EXIT1=SAR bearish · EXIT2=KAMA+SAR</p>
  </div>
  <div style="padding:16px">{banner}
    <table style="width:100%;border-collapse:collapse;font-size:12px">
      <thead><tr style="background:#f5f7fa">
        <th style="padding:6px;text-align:left;border-bottom:2px solid #d0d7de">Ticker</th>
        <th style="padding:6px;border-bottom:2px solid #d0d7de">Cat</th>
        <th style="padding:6px;text-align:left;border-bottom:2px solid #d0d7de">Nome</th>
        <th style="padding:6px;border-bottom:2px solid #d0d7de">Da</th>
        <th style="padding:6px;border-bottom:2px solid #d0d7de"></th>
        <th style="padding:6px;border-bottom:2px solid #d0d7de">A</th>
        <th style="padding:6px;border-bottom:2px solid #d0d7de">Prezzo</th>
        <th style="padding:6px;border-bottom:2px solid #d0d7de">Score</th>
        <th style="padding:6px;border-bottom:2px solid #d0d7de">Data</th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>
    <p style="margin-top:12px;font-size:11px;color:#57606a">
      📊 <a href="https://giorgiogoldoni.github.io/raptor-one/">Apri RAPTOR One</a> &nbsp;·&nbsp; ⚠️ Solo uso educativo
    </p>
  </div>
</div></body></html>'''.format(
        ts=now.strftime('%d/%m/%Y %H:%M'), reg=regime,
        vx=vix, vs=vstoxx, vc=vix_c, banner=banner, rows=rows)

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subj
        msg['From']    = EMAIL_USER
        msg['To']      = EMAIL_USER
        msg.attach(MIMEText(html, 'html'))
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as srv:
            srv.login(EMAIL_USER, EMAIL_PASS)
            srv.sendmail(EMAIL_USER, EMAIL_USER, msg.as_string())
        print(f"Email inviata: {len(alerts)} alert")
    except Exception as e:
        print(f"Errore email: {e}")

# ═══════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════
def main():
    now = datetime.datetime.now()
    print(f"RAPTOR Fetch v2.0 — {now.strftime('%Y-%m-%d %H:%M')}")
    print(f"Ticker totali universe: {len(TICKERS_ALL)}")
    print(f"Ticker dopo filtro: {len(TICKERS)} (esclusi BOND/Liquidita/Obbligazionari)")

    print("Fetching VIX/VSTOXX...")
    regime = fetch_vix_regime()
    print(f"  VIX={regime['vix']} VSTOXX={regime['vstoxx']} Regime={regime['regime']}")

    results, errors = [], 0
    for i, info in enumerate(TICKERS):
        result = process_ticker(info, regime['mult'])
        if result:
            results.append(result)
        else:
            errors += 1
        if (i+1) % 50 == 0:
            print(f"  {i+1}/{len(TICKERS)} — ok:{len(results)} errori:{errors}")
        time.sleep(0.3)

    # Conteggio segnali
    counts = {}
    for r in results:
        s = r.get('segnale','')
        counts[s] = counts.get(s,0) + 1
    print(f"\nSegnali: {counts}")

    # Rilevamento cambi per alert
    prev_segnali   = {}
    prev_regime_str = ''
    try:
        with open('raptor_data.json','r',encoding='utf-8') as f:
            prev = json.load(f)
            for r in prev.get('data',[]):
                prev_segnali[r['ticker']] = r.get('segnale','')
            prev_regime_str = prev.get('regime','')
    except: pass

    regime_changed = prev_regime_str and prev_regime_str != regime['regime']

    # Cambi che generano alert
    CAMBI_ALERT = {
        ('','BUY1'),('WATCH','BUY1'),('EXIT1','BUY1'),('EXIT2','BUY1'),
        ('','BUY2'),('WATCH','BUY2'),('EXIT1','BUY2'),
        ('','BUY3'),('WATCH','BUY3'),
        ('BUY1','EXIT1'),('BUY2','EXIT1'),('BUY3','EXIT1'),
        ('BUY1','EXIT2'),('BUY2','EXIT2'),('BUY3','EXIT2'),
    }
    SCORE_MIN = 50

    alerts = []
    for r in results:
        old = prev_segnali.get(r['ticker'],'')
        new = r.get('segnale','')
        if old != new and (old,new) in CAMBI_ALERT and r.get('score',0) >= SCORE_MIN:
            alerts.append({
                'ticker':    r['ticker'],
                'nome':      r.get('nome',''),
                'categoria': r.get('categoria',''),
                'old':       old or '—',
                'new':       new,
                'score':     r['score'],
                'prezzo':    r['prezzo'],
                'entry':     r.get('entryDate','—'),
            })

    print(f"Alert cambio segnale: {len(alerts)}")
    if alerts or regime_changed:
        send_alert_email(alerts, regime['vix'], regime['vstoxx'],
                        regime['regime'], now,
                        prev_regime_str if regime_changed else None)

    output = {
        'timestamp':     now.isoformat(),
        'timestamp_it':  now.strftime('%d/%m/%Y %H:%M'),
        'version':       '2.0',
        'total':         len(TICKERS),
        'ok':            len(results),
        'errors':        errors,
        'vix':           regime['vix'],
        'vstoxx':        regime['vstoxx'],
        'regime':        regime['regime'],
        'regime_mult':   regime['mult'],
        'regime_color':  regime['color'],
        'segnali_count': counts,
        'data':          results,
    }

    with open('raptor_data.json','w',encoding='utf-8') as f:
        json.dump(sanitize_nan(output), f, ensure_ascii=False, separators=(',',':'))

    print(f"\n✅ Salvato raptor_data.json — {len(results)} OK, {errors} errori")
    print(f"Regime: {regime['regime']} | VIX:{regime['vix']} VSTOXX:{regime['vstoxx']}")

if __name__ == '__main__':
    main()
