"""Clasifica cada producto en categoría, subcategoría y género, y ordena sus tallas.

Se lee primero el nombre del producto (lo más confiable). Si el nombre no dice qué es,
se usa la categoría que le pone la tienda y el enlace. Entre varias coincidencias gana
la palabra que aparece primero en el nombre: en "Pijama polar niño" manda "pijama".
"""
import re
import unicodedata


def sin_tildes(texto):
    t = unicodedata.normalize("NFD", (texto or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


# (categoría, subcategoría, patrón). Los patrones se aplican sobre texto en minúsculas y sin tildes.
REGLAS = [
    # ------------------------------------------------------------ Vestuario
    ("Vestuario", "Poleras", r"\bpoleras?\b|\bt-?shirts?\b|\btees?\b|\bcamisetas?\b|\btank\b|\bmusculosas?\b|\btops?\b|\bcrop\b|\btricotas?\b|\bjerseys?\b"),
    ("Vestuario", "Polerones y polares", r"\bpolerone?s?\b|\bhoodies?\b|\bsudaderas?\b|\bcanguros?\b|\bsweatshirts?\b|\bpolar(es)?\b|\bmicropolar\b|\bfleece\b|\bchiporros?\b"),
    ("Vestuario", "Chaquetas, parkas y abrigos", r"\bchaquet(a|as|on|ones)\b|\bparkas?\b|\bjackets?\b|\bcortavientos?\b|\brompevientos?\b|\bblazers?\b|\bpuffa?\b|\bpuffers?\b|\babrigos?\b|\btapados?\b|\bimpermeables?\b|\bgillets?\b|\bchaquetillas?\b|\bsacos?\b(?! de dormir)|\bveston(es)?\b|\btrench\b|\bplumas?\b|\bsoftshell\b|\bbombers?\b|\banoraks?\b|\bcazadoras?\b|\bsobrecamisas?\b"),
    ("Vestuario", "Sweaters y chalecos", r"\bsweaters?\b|\btejid[oa]s?\b|\bswetters?\b|\bchalecos?\b|\bcardigans?\b|\bpullovers?\b|\bbeatles?\b|\bsueter(es)?\b|\bponchos?\b|\bcapas?\b(?! (base|termica))"),
    ("Vestuario", "Camisas y blusas", r"\bcamisas?\b(?! de dormir)|\bsobrecamisas?\b|\bblusas?\b|\bshirts?\b|\bguayaberas?\b|\bcamiseros?\b|\bkimonos?\b|\btunicas?\b"),
    ("Vestuario", "Jeans", r"\bjeans?\b|\bdenim\b|\bmom fit\b"),
    ("Vestuario", "Pantalones", r"\bpantal(on|ones)\b|\bpants?\b|\bchinos?\b|\bjoggers?\b|\bcargos?\b|\bpalazzos?\b|\bculottes?\b|\bpantalonetas?\b|\bpantys? deportiv"),
    ("Vestuario", "Shorts y bermudas", r"\bshorts?\b|\bbermudas?\b|\bfalda-?short\b|\bshort-?falda\b"),
    ("Vestuario", "Faldas", r"\bfaldas?\b|\bskirts?\b|\bminifaldas?\b"),
    ("Vestuario", "Vestidos y enteritos", r"\bvestidos?\b|\benteritos?\b|\bjumpsuits?\b|\boverol(es)?\b|\bjardineras?\b|\bmonos? (largo|corto)\b|\bdress\b"),
    ("Vestuario", "Calzas y leggings", r"\bcalzas?\b|\bleggings?\b|\bleggins?\b|\bpatas?\b(?! de)|\btights?\b|\bbikers?\b"),
    ("Vestuario", "Buzos y conjuntos", r"\bbuzos?\b|\btracksuits?\b|\bconjuntos?\b|\btwin ?sets?\b|\bsets? deportiv"),
    ("Vestuario", "Ropa interior", r"\bropa interior\b|\blenceria\b|\bconjuntos? (de )?(ropa interior|lenceria|encaje|sosten)|\bcalzon(es|cillos?)?\b|\bboxers?\b(?! de bano)|\bsosten(es)?\b|\bsujetador(es)?\b|\bbrasier(es)?\b|\bbralettes?\b|\btangas?\b|\bcolales?\b|\bcolaless?\b|\bpetos?\b|\bculotte\b|\bportaligas\b|\bligas?\b|\bbodys? (de encaje|reductor)|\bsoutien|\bpeto(s)? deportiv|\bbrassiere|\bbikini (calzon|ropa)|\bpantaletas?\b|\bhipsters?\b|\bslips?\b(?! ?on)|\btrusas?\b|\bfajas?\b|\bcamisetas? interior"),
    ("Vestuario", "Pijamas y ropa de dormir", r"\bpijamas?\b|\bpijma\b|\bbaby ?dolls?\b|\bcamisas? de dormir\b|\bbatas?\b(?! de bano)|\bsalidas? de cama|\bdormir\b|\bloungewear\b|\bnightgown|\bcamison(es)?\b|\bsacos? de dormir bebe"),
    ("Vestuario", "Trajes de baño", r"\btrajes? de bano\b|\bbikinis?\b|\btrikinis?\b|\bswim\w*\b|\baquashorts?\b|\bboxers? de bano\b|\bpareos?\b|\bbanador(es)?\b|\bmallas? de bano|\bpolera(s)? (uv|de agua|lycra)|\blycras? (de agua|uv)\b|\btrajes? de neopreno|\bwetsuit"),
    ("Vestuario", "Ropa térmica", r"\bprimeras? capas?\b|\bcapas? base\b|\bbase ?layers?\b|\btermic[oa]s?\b|\bthermal\b|\bsegunda piel\b"),
    ("Vestuario", "Bodys y piluchos", r"\bpiluchos?\b|\bbodys?\b|\bbodies\b|\bositos?\b|\bmamelucos?\b|\brompers?\b|\bajuar(es)?\b"),
    ("Vestuario", "Uniformes y ropa de trabajo", r"\buniformes?\b|\bdelantal(es)?\b|\bclinic[oa]s?\b|\bscrubs?\b|\bropa de trabajo\b|\bovero(l|les) de trabajo"),

    # ------------------------------------------------------------ Calzado
    ("Calzado", "Zapatillas", r"\bzapatillas?\b|\bsneakers?\b|\btrainers?\b|\btenis\b(?! de mesa)|\bsneaker\b|\bzapatillas? (de )?(running|futbol|basquetbol|trekking)"),
    ("Calzado", "Zapatos", r"\bzapatos?\b|\bmocasin(es)?\b|\boxfords?\b|\bslip ?ons?\b|\bballerinas?\b|\bbailarinas?\b|\bflats?\b|\bderbys?\b|\bloafers?\b|\bnauticos?\b|\btacos?\b|\bstilettos?\b|\bpumps?\b|\bplataformas?\b|\bbluchers?\b|\bpanchas?\b|\bzapatos de seguridad\b"),
    ("Calzado", "Botas y botines", r"\bbotas?\b|\bbooties?\b|\bcover shoes?\b|\bbotin(es)?\b|\bbotitas?\b|\bboots?\b|\bbototos?\b|\bbotinetas?\b|\bbotas? de agua|\bcaña alta\b"),
    ("Calzado", "Sandalias y chalas", r"\bsandalias?\b|\bchalas?\b|\bojotas?\b|\bhawaianas?\b|\bflip ?flops?\b|\balpargatas?\b|\bzuecos?\b|\bclogs?\b|\bcrocs\b|\bslides?\b|\bsuecos?\b|\bzapatillas? de playa|\bsandalet"),
    ("Calzado", "Pantuflas", r"\bpantuflas?\b|\bslippers?\b|\bchinelas?\b"),

    # ------------------------------------------------------------ Accesorios
    ("Accesorios", "Mochilas", r"\bmochilas?\b|\bbackpacks?\b"),
    ("Accesorios", "Bolsos y carteras", r"\bbolsos?\b|\bbolsas? (mujer|hombre|de cuero|de mano)|\blongstraps?\b|\bsobres? (plano|reptil|de mano|cartera)|\bcarteras?\b|\bbananos?\b|\brinoneras?\b|\btotes?\b|\btote ?bags?\b|\bbandoleras?\b|\bbags?\b|\bclutch\b|\bmorral(es)?\b|\bshoppers?\b|\bbolsas? (de playa|deportiv|matera)|\bcrossbody\b|\bpouch\b|\bsobres? de mano"),
    ("Accesorios", "Billeteras", r"\bbilleteras?\b|\bmonederos?\b|\btarjeteros?\b|\bwallets?\b|\bporta ?documentos\b|\bporta ?tarjetas?\b"),
    ("Accesorios", "Gorros y jockeys", r"\bgorr[oa]s?\b(?! de natacion)|\bjockeys?\b|\bcaps?\b|\bsombreros?\b|\bbeanies?\b|\bviseras?\b|\bboinas?\b|\bbandanas?\b|\bbucket\b|\bpasamontanas?\b|\bcintillos?\b|\bbalaclavas?\b|\btrucker\b"),
    ("Accesorios", "Lentes", r"\blentes?\b|\banteojos\b|\bgafas\b|\bsunglasses\b|\blentes de sol\b"),
    ("Accesorios", "Relojes", r"\breloj(es)?\b|\bwatch(es)?\b|\bcorreas? (de |para )?reloj"),
    ("Accesorios", "Joyas y bisutería", r"\bcollar(es)?\b(?! (para|de) (perro|gato|mascota))|\baros?\b(?! \d)|\bpulseras?\b|\banillos?\b|\bjoyas?\b|\bjoyeros?\b|\bbisuteria\b|\bcolgantes?\b|\baretes?\b|\bpendientes?\b|\bbroches?\b|\bcadenas? de (plata|oro)|\bdijes?\b|\btobilleras?\b|\bpiercings?\b|\bargollas?\b|\bearrings?\b|\bnecklaces?\b"),
    ("Accesorios", "Cinturones", r"\bcinturon(es)?\b|\bbelts?\b|\btirantes?\b|\bsuspensor(es)?\b"),
    ("Accesorios", "Calcetines y medias", r"\bcalcetin(es)?\b|\bcalcetas?\b|\bsocks?\b|\bsoquetes?\b|\bmedias\b|\bmini medias?\b|\bmedias? (mujer|nylon|panty)\b|\bpantys?\b(?! deportiv)|\bballerinas? (calcetin|invisible)|\bmedias? panty"),
    ("Accesorios", "Bufandas, guantes y cuellos", r"\bbufandas?\b|\bguantes?\b|\bcuellos?\b(?! (v|redondo|camisero|polo|alto|tortuga))|\bpashminas?\b|\bchal(es)?\b|\bmiton(es)?\b|\bmitts?\b|\bpanuelos?\b|\bfoulards?\b|\bneck ?gaiters?\b|\borejeras?\b|\bcorbatas?\b|\bhumitas?\b|\bpajaritas?\b"),
    ("Accesorios", "Maletas y viaje", r"\bmaletas?\b|\bmaletin(es)?\b|\bequipajes?\b|\bcandados?\b|\bviajes?\b|\bneceser(es)?\b|\bcojin(es)? (inflable|de viaje|cervical)|\bcarry ?on\b|\bportatrajes?\b|\bcubos? organizador|\bbolsos? de viaje|\btrolleys?\b|\bset de maletas"),
    ("Accesorios", "Paraguas", r"\bparaguas\b|\bsombrillas?\b"),
    ("Accesorios", "Accesorios para el pelo", r"\bpinches?\b|\bcoles? de pelo\b|\bscrunchies?\b|\btrabas?\b|\bpeinetas?\b|\bdiademas?\b|\bcolets?\b|\bmonos? (de pelo|para el pelo)|\bcoleros?\b|\bpinzas? (de|para) (pelo|cabello)"),

    # ------------------------------------------------------------ Deportes
    ("Deportes", "Bicicletas y rodados", r"\bbicicletas?\b(?! estatica)|\bbicis?\b|\bciclismo\b|\bscooters?\b|\bmonopatin(es)?\b|\bpatinetas?\b|\bpatinetes?\b|\bskates?\b|\bskateboards?\b|\bpatines\b|\brollers?\b|\blongboards?\b|\bcascos?\b|\bpedal(es)?\b|\bsillin(es)?\b|\bcaramayolas?\b|\bportacaramayolas?\b|\bporta caramayolas?\b|\bbontrager\b|\bmazas?\b|\bcadenas? (de )?bicicleta|\bcambios? (shimano|sram)|\bshimano\b|\bneumaticos? (de )?bicicleta|\bcamaras? (de )?bicicleta"),
    ("Deportes", "Camping y outdoor", r"\bcarpas?\b|\bsacos? de dormir\b|\bcamping\b|\bcolchonetas?\b|\bbaston(es)? (de )?trekking|\bbaston(es)?\b|\blinternas?\b|\bconservadora|\bcoolers?\b|\bhamacas?\b|\bmochilas? de hidratacion|\bcantimploras?\b|\bnavajas?\b|\bcortaplumas?\b|\banafes?\b|\bsillas? de camping|\bmesas? de camping|\bbrujulas?\b|\bdry ?bags?\b"),
    ("Deportes", "Fitness y gimnasio", r"\bmancuernas?\b|\bpesas\b|\bpesa rusa\b|\bkettlebells?\b|\bmats?\b|\byoga\b|\bpilates\b|\bbandas? elasticas?\b|\bbandas? de resistencia|\btrotadoras?\b|\belipticas?\b|\bbicicletas? estaticas?\b|\bbancos? de (ejercicio|pesas|abdominales)|\bfitness\b|\bhand ?grips?\b|\bbarras? de masaje|\bmasaje muscular|\bdiscos? (de pesas|olimpico)|\bbarras? (olimpica|de dominadas)|\bcuerdas? de saltar|\bcomba\b|\bmuñequeras?\b|\brodilleras?\b|\btobilleras? (de peso|lastre)|\bfoam roller\b|\bpelota de pilates\b|\bsteps?\b|\bremos? (de )?(ergometro|indoor)|\bspinning\b"),
    ("Deportes", "Balones y deportes de equipo", r"\bbalon(es)?\b|\bpelotas?\b|\barcos? (de )?futbol\b|\braquetas?\b|\bpaletas? (de )?(padel|ping ?pong|playa)|\bpadel\b|\btenis de mesa\b|\bvoleibol\b|\bbasquetbol\b|\bfutbolitos?\b|\bcanilleras?\b|\bguantes? de arquero|\btaca(s|chos)? (de )?futbol|\bmesas? de ping"),
    ("Deportes", "Natación y deportes acuáticos", r"\bantiparras?\b|\bgorros? de natacion|\baletas?\b|\bsnorkel\b|\bflotador(es)?\b|\btablas? (de surf|bodyboard|de natacion|stand ?up|sup)\b|\bkayaks?\b|\bchalecos? salvavidas\b|\bbodyboard"),
    ("Deportes", "Pesca y caza", r"\bpesca\b|\bcanas? de pescar|\bcarretes?\b|\bseñuelos?\b"),

    # ------------------------------------------------------------ Tecnología
    ("Tecnología", "Smartwatch y wearables", r"\breloj(es)? inteligentes?\b|\bsmart ?watch(es)?\b|\bsmart ?bands?\b|\bbandas? inteligentes?\b|\bpulseras? (inteligente|de actividad)|\bmi band\b|\bgalaxy watch\b|\bapple watch\b|\bamazfit\b"),
    ("Tecnología", "Celulares", r"\bcelular(es)?\b|\bsmartphones?\b|\biphone\b|\bgalaxy [asz]\d|\bredmi\b|\bmotorola (moto|edge)|\bxiaomi \d|\bpoco [xmf]\d"),
    ("Tecnología", "Computación", r"\bnotebooks?\b|\blaptops?\b|\bcomputador(es|as)?\b|\bpcs?\b|\bmacbook\b|\bmonitor(es)?\b|\bteclados?\b|\bmouses?\b|\bimpresoras?\b|\bdiscos? (duro|ssd|externo)|\bpendrives?\b|\bssd\b|\brouters?\b|\ball in one\b|\bchromebook\b|\bwebcams?\b|\bmemorias? (usb|ram|micro ?sd)"),
    ("Tecnología", "Tablets", r"\btablets?\b|\bipad\b|\bgalaxy tab\b|\blector(es)? de libros|\bkindle\b"),
    ("Tecnología", "Televisores y video", r"\btelevisor(es)?\b|\btv\b|\bsmart tv\b|\bproyector(es)?\b|\bleds? \d{2}\b|\bqled\b|\boled\b|\bchromecast\b|\bfire ?stick\b|\btv ?box\b|\bsoportes? (de |para )?tv\b"),
    ("Tecnología", "Audio", r"\baudifonos?\b|\bauricular(es)?\b|\bparlantes?\b|\bheadphones?\b|\bheadsets?\b|\bearbuds?\b|\bsoundbars?\b|\bbarras? de sonido\b|\bmicrofonos?\b|\btornamesas?\b|\bequipos? de musica|\bminicomponentes?\b|\bradios?\b|\bairpods\b|\bbuds\b"),
    ("Tecnología", "Videojuegos", r"\bconsolas?\b|\bplaystation\b|\bps[345]\b|\bnintendo\b|\bswitch\b|\bxbox\b|\bvideojuegos?\b|\bjoysticks?\b|\bjuegos? (ps|xbox|switch|nintendo)|\bcontrol(es)? (inalambrico|ps|xbox|dualsense)|\bgamer\b|\bgaming\b"),
    ("Tecnología", "Cámaras y drones", r"\bcamaras?\b(?! de seguridad)|\bgopro\b|\bdron(es)?\b|\btripodes?\b|\blentes? (para camara|fotografic)|\bmirrorless\b"),
    ("Tecnología", "Accesorios de tecnología", r"\bcargador(es)?\b|\bcables?\b|\bcarcasas?\b|\bfundas? (para )?(celular|iphone|samsung|notebook|tablet|ipad)|\bmicas?\b|\bpilas?\b|\bbaterias? recargables?|\bcontrol(es)? remotos?|\bprotector(es)? de pantalla|\bpower ?banks?\b|\bbaterias? (externa|portatil)|\badaptador(es)?\b|\bhubs?\b|\bsoportes? (para|de) (celular|notebook|monitor)|\blapiz (optico|digital)|\bstylus\b|\balmohadillas? mouse|\bmouse ?pads?\b"),

    # ------------------------------------------------------------ Electrohogar
    ("Electrohogar", "Refrigeración", r"\brefrigerador(es|as)?\b|\bfreezers?\b|\bcongelador(es)?\b|\bfrigobar(es)?\b|\bvineras?\b|\bdispensador(es)? de agua"),
    ("Electrohogar", "Lavado y planchado", r"\blavadoras?\b|\bsecadoras?\b(?! de pelo)|\blavavajillas\b|\blavaseca(s|doras?)?\b|\bplanchas?\b(?! de pelo)|\bvaporizador(es)?\b|\bcentrifugas?\b"),
    ("Electrohogar", "Cocina y pequeños electrodomésticos", r"\bhornos?\b|\bmicroondas\b|\bfreidoras?\b|\bair ?fryers?\b|\bcafeteras?\b|\bhervidor(es|as)?\b|\blicuadoras?\b|\bbatidoras?\b|\bjugueras?\b|\bextractor(es)? de jugo|\bsandwicheras?\b|\btostadoras?\b|\bprocesadoras?\b|\bollas? (electricas?|arroceras?|multifuncion|a presion electrica|de coccion lenta)|\barroceras?\b|\bcocinas? (a gas|electricas?|de induccion|encimera)|\bencimeras?\b|\bcampanas?\b|\bwafleras?\b|\bmaquinas? de (cafe|pan|helado|pasta)|\bminipimers?\b|\bmixers?\b|\byogurteras?\b|\bplanchas? (asadora|grill)|\bparrillas? electricas?|\bteteras? electricas?|\bmolinillos?\b|\bespumador(es)?\b"),
    ("Electrohogar", "Aspirado y limpieza", r"\baspiradoras?\b|\brobots? aspirador|\bmopas? a vapor\b|\benceradoras?\b|\blimpiador(es|as)? a vapor|\bescobas? electricas?"),
    ("Electrohogar", "Climatización", r"\bestufas?\b|\bcalefactor(es)?\b|\bventilador(es)?\b|\baire acondicionado\b|\bpurificador(es)?\b|\bhumidificador(es)?\b|\bdeshumidificador(es)?\b|\boleoelectricos?\b|\bguateros? electricos?\b|\bcalienta ?camas\b|\bcolchon(es)? electricos?\b|\bfrazadas? electricas?|\bclimatizador(es)?\b|\bpanel(es)? calefactor"),
    ("Electrohogar", "Cuidado personal eléctrico", r"\bsecador(es|as)? de pelo\b|\balisador(es|as)?\b|\bplanchas? de pelo\b|\bonduladoras?\b|\brizadoras?\b|\bafeitadoras?\b|\brasuradoras?\b|\bdepiladoras?\b|\bcortapelos?\b|\bcortadoras? de pelo|\brecortadoras?\b|\bcepillos? (electricos?|alisador|secador)|\bmaquinas? de afeitar|\btrimmers?\b|\birrigador(es)? (dental|bucal)"),

    # ------------------------------------------------------------ Muebles y hogar
    ("Muebles y hogar", "Sofás y sillones", r"\bsofas?\b|\bsitial(es)?\b|\bliving\b|\bbergeres?\b|\bsillon(es)?\b|\bsofa ?camas?\b|\bfuton(es)?\b|\bseccional(es)?\b|\bpoltronas?\b|\bpuffs?\b|\bpoufs?\b|\bchaise ?longues?\b|\bmodular(es)?\b|\bdivan(es)?\b|\breclinables?\b|\blove ?seat\b"),
    ("Muebles y hogar", "Sillas y taburetes", r"\bsillas?\b|\btaburetes?\b|\bbanquetas?\b|\bpisos? (de )?bar\b|\bbancas?\b|\bbutacas?\b"),
    ("Muebles y hogar", "Mesas y escritorios", r"\bmesas?\b(?! de noche)|\bmeson(es)?\b|\bescritorios?\b|\bcomedor(es)?\b|\bmesas? de centro\b|\bmesas? laterale?s?\b|\bmesitas?\b|\barrimos?\b|\bconsolas? (de entrada|mueble)"),
    ("Muebles y hogar", "Camas y colchones", r"\bcamas?\b(?! (para|de) (perro|gato|mascota))|\bcolchon(es)?\b|\bbox ?springs?\b|\brespaldos?\b|\bbases? (de )?cama\b|\bvelador(es)?\b|\bmesas? de noche\b|\bcatres?\b|\bliteras?\b|\bcamarotes?\b|\bdivan(es)? cama|\bset (2vel|veladores)|\b2vel\b|\b\d ?plazas?\b|\bking\b|\bqueen\b"),
    ("Muebles y hogar", "Ropa de cama", r"\bsabanas?\b|\bplumon(es)?\b|\bquilts?\b|\bcubrecamas?\b|\bcobertor(es)?\b|\bfrazadas?\b|\bmantas?\b|\bfundas? (de )?(almohada|plumon|nordica|duvet)|\bfaldon(es)?\b|\bduvets?\b|\bcubre ?colchon(es)?\b|\bprotector(es)? de colchon|\balmohadas?\b|\bplaids?\b|\bjuegos? de sabanas|\bcubre ?plumon(es)?\b|\btoppers?\b|\bpie de cama\b|\bpieceras?\b"),
    ("Muebles y hogar", "Baño", r"\btoallas?\b|\btoallon(es)?\b|\balfombras? de bano|\bcortinas? de bano|\bdispensador(es)?\b|\bjaboneras?\b|\bsets? de bano|\bbatas? de bano|\bcepilleros?\b|\bporta ?cepillos?\b|\bbasureros? de bano|\bpisos? de bano\b"),
    ("Muebles y hogar", "Cocina y mesa", r"\bollas?\b|\bsartene?s?\b|\bbaterias? de (cocina|aluminio|acero|ollas)\b|\bmoledor(es|as?)?\b|\btrituradoras? de carne|\bpicador(es)?\b|\bfil(e|ea)teador(es)?\b|\bpelador(es)?\b|\bbatidor(es)?\b|\bmortero\b|\btijeras? (de |para )?(cocina|cortar pizza|pizza)|\bjeringas?\b|\bgarras? para carne|\bsets? (de )?servicio|\balcuzas?\b|\b(set (\d )?)?accesorios? para (fruta|cocina)|\bestacas? para sostener|\bvajillas?\b|\bplatos?\b|\bvasos?\b|\btazas?\b|\btazon(es)?\b|\bcopas?\b|\bcuchillos?\b|\bcubiertos?\b|\bbotellas?\b|\btermos?\b|\bcontenedor(es)?\b|\bhermeticos?\b|\btablas? (de )?(picar|cortar|quesos?)|\butensilios?\b|\bmoldes?\b|\bbandejas?\b|\bjarros?\b|\bjarras?\b|\bteteras?\b|\bmugs?\b|\bpaneras?\b|\bescurridor(es)?\b|\bsecaplatos\b|\bbowls?\b|\bpocillos?\b|\bfuentes?\b|\bloncheras?\b|\bgrameras?\b|\bpesas? (de )?cocina\b|\bespatulas?\b|\bcuchar(a|as|on|ones)\b|\brallador(es)?\b|\bcolador(es)?\b|\bmantel(es)?\b|\bindividual(es)?\b|\bposavasos\b|\bservilleteros?\b|\baceiteras?\b|\bsaleros?\b|\bcafeteras? (italiana|de embolo|french press)|\bprensas? francesas?\b|\bwoks?\b|\bpailas?\b|\bcacerolas?\b|\bbudineras?\b|\bqueques?\b|\bpiezas? de cocina|\bporta ?esponjas?\b|\bpanos? de cocina|\bdelantal(es)? de cocina|\bfrascos?\b|\bmaterus?\b|\bmates?\b|\bbombillas?\b|\bdecantador(es)?\b|\bhieleras?\b|\bcocteleras?\b|\bcuchillerias?\b"),
    ("Muebles y hogar", "Iluminación", r"\blamparas?\b|\bampolletas?\b|\bfocos?\b|\bapliques?\b|\bluminarias?\b|\bguirnaldas?\b|\bluces\b|\bpanel(es)? led\b|\bcintas? led\b|\btiras? led\b|\bplafon(es)?\b|\bcolgantes? de techo|\bvelador(es)? (de )?(luz|lampara)|\blamparas? de (pie|mesa|techo)"),
    ("Muebles y hogar", "Cortinas y alfombras", r"\bcortinas?\b|\bpersianas?\b|\bvisillos?\b|\bblackout\b|\bbarras? (de |para )?cortina|\balfombras?\b|\blimpiapies\b|\bbajadas? de cama\b|\bpisos? (vinilico|alfombra)|\bpelaje\b|\bbajadas?\b"),
    ("Muebles y hogar", "Decoración", r"\bcuadros?\b|\bespejos?\b|\bjarron(es)?\b|\bfloreros?\b|\bvelas?\b|\bdifusor(es)?\b|\bcojin(es)?\b|\bdecoraci\w*\b|\bdecorativ\w*\b|\bportarretratos?\b|\bplantas? artificiales?\b|\bflor(es)? artificiales?\b|\b(rosas?|ramos?|hojas?) artificiales?\b|\bletreros?\b|\bneon\b|\bfiguras?\b|\besculturas?\b|\breloj(es)? de pared\b|\bvinilos? decorativ|\bposters?\b|\bornamentos?\b|\bnavide\w*\b|\barbol(es)? de navidad|\bpesebres?\b|\bcandelabros?\b|\bportavelas?\b|\bfundas? de cojin|\baromatizador(es)?\b|\bfragancias? (para el )?hogar|\bvarillas? aromatic"),
    ("Muebles y hogar", "Organización y almacenaje", r"\borganizador(es)?\b|\bcajas?\b|\bperchas?\b|\bganchos?\b|\bzapateros?\b|\bclosets?\b|\broperos?\b|\bcomodas?\b|\bcajoneras?\b|\brepisas?\b|\bestantes?\b|\bestanterias?\b|\blibreros?\b|\bmuebles?\b|\bracks?\b|\bbaul(es)?\b|\bcanastos?\b|\bcestos?\b|\bcanastas?\b|\bpercheros?\b|\bburos?\b|\bvitrinas?\b|\baparador(es)?\b|\bbuffets?\b|\bbibliotecas?\b|\bcolgador(es)?\b|\bbasureros?\b|\bpapeleros?\b|\bcarros? (organizador|de cocina|auxiliar)"),
    ("Muebles y hogar", "Limpieza del hogar", r"\bescobas?\b|\btraperos?\b|\bmopas?\b|\bbaldes?\b|\bpalas? de basura|\bdetergentes?\b|\blimpiador(es)?\b|\bdesinfectantes?\b|\bpanos? de limpieza|\bplumeros?\b|\btendederos?\b|\bcolgador(es)? de ropa|\bpinzas? de ropa|\bcanastos? de ropa"),

    # ------------------------------------------------------------ Belleza y salud
    ("Belleza y salud", "Perfumes", r"\bperfumes?\b|\bcolonias?\b|\bfragancias?\b|\beau de (parfum|toilette|cologne)\b|\bedp\b|\bedt\b|\bbody (mist|splash)\b|\bsplash\b|\bsprays? (corporal|hombre|mujer|incoloro|varios)|\bparfum\b"),
    ("Belleza y salud", "Maquillaje", r"\bmaquillajes?\b|\blabial(es)?\b|\bbases? (de )?maquillaje\b|\bbases? liquidas?|\bmascaras? de pestanas\b|\bmascaras? (para )?pestanas|\bdelineador(es)?\b|\bsombras?\b|\brubor(es)?\b|\bpolvos?\b|\bcorrector(es)?\b|\besmaltes?\b|\bbrochas?\b|\bpaletas? de (sombras|maquillaje|rubor)|\bbrillos? labiales?\b|\bgloss\b|\bprimers?\b|\biluminador(es)?\b|\bbronceador(es)?\b|\bpestanas postizas|\bcejas\b|\blip\b|\bkajal\b|\bcushion\b|\bbb cream\b|\bcc cream\b|\bsetting spray\b"),
    ("Belleza y salud", "Cuidado de la piel", r"\bcremas?\b|\bserums?\b|\bsueros? facial(es)?\b|\bprotector(es)? solar(es)?\b|\bbloqueador(es)?\b|\bfotoprotector(es)?\b|\bhidratantes?\b|\blimpiador(es)? facial(es)?\b|\bmascarillas?\b(?! capilar)|\btonicos?\b|\bcontorno de ojos\b|\bdesodorantes?\b|\bantitranspirantes?\b|\bjabon(es)?\b|\bexfoliantes?\b|\bgel(es)? de ducha\b|\bbody lotion\b|\blocion(es)?\b|\baceites? (corporal|facial)|\bagua micelar\b|\bmicelar\b|\bdermo\w*\b|\bacne\b|\bretinol\b|\bhialuronico\b|\bvitamina c\b|\bmanteca corporal|\bbalsamo labial\b|\bcuidado facial|\btoallitas? (faciales|desmaquillantes)|\brodillos? facial|\bcuidado corporal|\bautobronceante"),
    ("Belleza y salud", "Cuidado del cabello", r"\bshampoos?\b|\bchampus?\b|\bacondicionador(es)?\b|\btratamientos? capilar(es)?\b|\bmascarillas? capilar(es)?\b|\btinturas?\b|\bcapilar(es)?\b|\bcremas? (de )?peinar\b|\bsprays? (para el )?pelo|\bgel(es)? (para el )?pelo|\bceras? (para el )?pelo|\bpomadas? capilar|\bkeratinas?\b|\boleos? capilar|\bleave ?in\b"),
    ("Belleza y salud", "Salud y bienestar", r"\bvitaminas?\b|\bsuplementos?\b|\bcapsulas?\b|\bcomprimidos?\b|\bproteinas?\b|\bwhey\b|\bcreatina\b|\bcolagenos?\b|\bomega\b|\bmagnesio\b|\bmelatonina\b|\bprobioticos?\b|\bcompresas?\b|\btermometros?\b|\bmasajeador(es)?\b|\btensiometros?\b|\boximetros?\b|\bnebulizador(es)?\b|\bbotiquin(es)?\b|\bmultivitaminico\b|\bcepillos? de dientes|\bpastas? dental(es)?|\benjuagues? bucal(es)?|\bhilo dental\b|\bpreservativos?\b|\blubricantes?\b|\bmascarillas? (desechables|kn95|n95)|\bgel antibacterial|\balcohol gel"),
    ("Belleza y salud", "Manicure y accesorios de belleza", r"\bmanicure\b|\bpedicure\b|\blimas?\b|\bcortaunas\b|\bespejos? de (maquillaje|aumento)|\bneceser(es)? de maquillaje|\besponjas? de maquillaje|\bpinzas? (de )?cejas|\bencrespador(es)?\b|\bpeines?\b|\bcepillos? (de pelo|para el pelo|desenredante)"),

    # ------------------------------------------------------------ Infantil (juguetes y artículos de bebé)
    ("Infantil", "Juguetes", r"\bjuguetes?\b|\bpeluches?\b|\bmunecas?\b|\bmunecos?\b|\blego\b|\bpuzzles?\b|\brompecabezas\b|\bjuegos? de mesa\b|\bbloques? (de construccion|didacticos)|\bdidactic\w*\b|\bmontables?\b|\bplay ?doh\b|\bplasticina\b|\bbarbie\b|\bhot ?wheels\b|\bfiguras? de accion\b|\bpistas? de autos|\bautos? (a control|de juguete|radio ?control|a batería)|\bcocinitas?\b|\bcasas? de munecas|\bnerf\b|\bslime\b|\bjuegos? (de agua|didactico|infantil)|\bsonajeros?\b|\bmordedor(es)?\b|\bgimnasios? (para )?bebe|\bpelota saltarina|\btrampolin(es)?\b|\bresbalin(es)?\b|\bcolumpios?\b|\bpiscinas? (inflable|infantil)|\bdisfraces?\b|\bdisfraz\b|\bgo ?karts?\b|\barmables?\b|\bmotos? a bateria\b|\bautos? a bateria\b|\btummy time\b|\bpianos? (de )?juguete|\bjuegos? armables?|\bsets? armables?"),
    ("Infantil", "Coches y sillas de auto", r"\bcoches?\b|\bsillas? (de |para )?auto\b|\balzador(es)?\b|\bportabebes?\b|\bbutacas? (de |para )?auto|\btravel ?systems?\b|\bcoches? paragua|\bcochecitos?\b|\bcargador(es)? (de )?bebe|\bmochilas? portabebe|\bfular(es)?\b|\bbicicletas? de equilibrio|\bandador(es)?\b|\bcorrepasillos?\b"),
    ("Infantil", "Cunas y muebles de bebé", r"\bcunas?\b|\bpuertas? (de )?seguridad\b|\bdoor gate\b|\breja (de )?seguridad|\bcorral(es)?\b|\bmudador(es)?\b|\bsillas? (de )?comer\b|\bmecedoras?\b|\bnidos?\b|\bbaneras?\b|\bcolechos?\b|\bmoises\b|\bcatres? de viaje|\bcuna corral|\bbouncers?\b|\bhamacas? (para )?bebe|\bmonitor(es)? (de |para )?bebe|\bbaby ?call\b"),
    ("Infantil", "Lactancia y alimentación", r"\b(extractor(es)?|colector(es)?) (de )?leche materna\b|\bmamaderas?\b|\bchupetes?\b|\bextractor(es)? de leche\b|\bbaberos?\b|\btetinas?\b|\besterilizador(es)?\b|\bvasos? (de )?(entrenamiento|aprendizaje)|\bcojin(es)? de lactancia|\bpanal(es)?\b|\btoallitas? humedas\b|\bcambiador(es)?\b"),
    ("Infantil", "Escolar", r"\bescolar(es)?\b|\bestuches?\b|\bcuadernos?\b|\blapices?\b|\bplumon(es)? (de )?colores|\btemperas?\b|\bacuarelas?\b|\bcroqueras?\b|\butiles\b|\bagendas?\b|\bplanificador(es)?\b|\bcalculadoras?\b"),

    # ------------------------------------------------------------ Mascotas
    ("Mascotas", "Alimento para mascotas", r"\b(perro|gato|cachorro|felino|canino)s? (adulto|senior|cachorro|kitten|puppy|esterilizado)s?\b|\bcats?\b|\bdogs?\b|\bkitten\b|\bpuppy\b|\bhierba gatera\b|\balimentos? (para |de )?(perro|gato|mascota|cachorro|felino|canino)s?|\bcomida (para )?(perro|gato)|\bpellets?\b|\bsnacks? (para )?(perro|gato)|\bpremios? (para )?(perro|gato)|\bproplan\b|\bpro plan\b|\broyal canin\b|\bacana\b|\borijen\b|\bbrit\b|\bhills\b|\bmaster dog\b|\bmaster cat\b|\bdog chow\b|\bcat chow\b|\bwhiskas\b|\bfit formula\b|\bnutrience\b"),
    ("Mascotas", "Accesorios para mascotas", r"\bmascotas?\b|\bcamas? (para |de )?(perro|gato|mascota)|\bcollar(es)? (para |de )?(perro|gato|mascota)|\bcorreas? (para |de )?(perro|gato|mascota)|\bcorreas? retractil|\barnes(es)?\b|\barena (sanitaria|para gato)|\brascador(es)?\b|\btransportador(es|as)?\b|\bcomederos?\b|\bbebederos?\b|\bjuguetes? (para )?(perro|gato)|\bsanitarios? (para )?gato|\bpecheras?\b|\bcanil(es)?\b|\bacuarios?\b|\bpipetas?\b|\bantipulgas\b|\blitter\b|\bpiedras? sanitarias?"),

    # ------------------------------------------------------------ Alimentos y bebidas
    ("Alimentos y bebidas", "Frutos secos y snacks", r"\bfrutos? secos\b|\bnuec(es)?\b|\bnuez\b|\balmendras?\b|\bmani(es)?\b|\bpistachos?\b|\bcastanas?\b|\bavellanas?\b|\bpasas\b|\bdatiles\b|\bmix (de )?frutos|\bsnacks?\b(?! (para )?(perro|gato))|\bchips\b|\bpapas fritas\b|\bbarras? (de )?cereal|\bbarritas?\b|\bcranberries\b|\barandanos? deshidratados|\bdeshidratad[oa]s?\b|\bsemillas? de (chia|maravilla|zapallo|linaza)"),
    ("Alimentos y bebidas", "Despensa", r"\bcafe(s)? (en grano|molido|de grano|instantaneo|tostado|de especialidad|organico)|\bcapsulas? de cafe|\bcafe espresso\b|\bte (verde|negro|chai|rojo|blanco)\b|\binfusion(es)?\b|\btisanas?\b|\bmatcha\b|\byerba mate\b|\bchocolates? (amargo|de leche|blanco|bitter|semi\w*|en barra|\d+ ?%)|\b(barras?|tabletas?) de chocolate|\bbombones?\b|\bgalletas?\b|\bmermeladas?\b|\bmanjar\b|\bmiel\b|\bpastas? (de trigo|integral|fresca|seca)|\bfideos?\b|\btallarines\b|\barroz\b|\bharinas?\b|\bgranolas?\b|\bavena\b|\bquinoa\b|\bespecias?\b|\bcondimentos?\b|\bmerken\b|\bsal (de mar|parrillera|de mesa|rosada|de cahuil)|\bazucar\b|\baceites? (de oliva|de coco|vegetal|de maravilla|de palta)|\baceite de oliva\b|\bvinagres?\b|\bsalsas?\b|\bpesto\b|\bconservas?\b|\bmantequillas? de (mani|almendra)|\bpan(es)?\b|\bcereales?\b|\bpasteleria\b|\bturron(es)?\b|\bcalugas?\b|\balfajor(es)?\b|\bprotein bar"),
    ("Alimentos y bebidas", "Bebidas y licores", r"\bvinos?\b|\bcervezas?\b|\bjugos?\b|\bnectar(es)?\b|\baguas? (mineral|purificada|con gas|sin gas|saborizada)|\bbebidas?\b|\blicor(es)?\b|\bpisco\b|\bwhisky\b|\bgin\b|\bron\b|\bvodka\b|\btequila\b|\bespumantes?\b|\bkombucha\b|\bsidra\b|\baperitivos?\b|\bcocteles?\b|\bcarmenere\b|\bcabernet\b|\bsauvignon\b|\bmerlot\b|\bchardonnay\b|\bsyrah\b|\bpais\b(?= ?(vino|cepa))"),
    ("Alimentos y bebidas", "Carnes, fiambres y quesos", r"\bcharcuteri\w*|\bjamon(es)?\b|\bsalames?\b|\blonganizas?\b|\bchorizos?\b|\bprosciutto\b|\bpancetas?\b|\btocino\b|\bfiambres?\b|\bpates?\b|\bquesos?\b|\bmantequilla\b|\byogurt\b|\bleche\b(?! (corporal|desmaquillante|limpiadora|materna|de magnesia))|\bcarnes?\b|\bpollo\b|\bvacuno\b|\bcerdo\b|\bsalmon\b|\bmariscos?\b|\bcecinas?\b|\bembutidos?\b"),
    ("Alimentos y bebidas", "Comidas preparadas y congelados", r"\bempanadas?\b|\bpizzas?\b|\bcomidas? preparadas?|\bcongelad[oa]s?\b|\bhelados?\b|\blasanas?\b|\bcanelones\b|\bsopas?\b|\bcremas? de (verdura|zapallo|tomate)|\bplatos? preparados?|\bcolaciones?\b|\bsushi\b|\bpasteles?\b|\btortas?\b|\bkuchen\b|\bqueques? de"),
    ("Alimentos y bebidas", "Frutas y verduras", r"\bcanastas? (de )?(frutas|verduras)|\bfrutas? (frescas?|deshidratadas?|confitadas?|de estacion)|\bverduras? (frescas?|congeladas?|organicas?)|\bhortalizas?\b"),

    # ------------------------------------------------------------ Ferretería y jardín
    ("Ferretería y jardín", "Herramientas", r"\bherramientas?\b|\bcajas? de herramientas\b|\btaladros?\b|\batornillador(es)?\b|\bsierras?\b|\besmeril(es|adoras?)?\b|\bllaves? (de )?(punta|corona|francesa|torque|allen)|\bdestornillador(es)?\b|\bmartillos?\b|\bcompresor(es)?\b|\bhidrolavadoras?\b|\bsoldadoras?\b|\bescaleras?\b|\bpinturas?\b|\brodillos? (de )?pintar|\bbrochas? (de )?pintar|\bcaladoras?\b|\blijadoras?\b|\bnivel(es)? (laser|de burbuja)|\bhuinchas?\b|\bbrocas?\b|\bbaterias? (de )?litio\b|\bgenerador(es)?\b|\bextension(es)? electricas|\balargador(es)?\b|\bzapatillas? electricas"),
    ("Ferretería y jardín", "Jardín y terraza", r"\bjardin(es)?\b|\bjardineria\b|\bpasto\b|\bestacas?\b|\benrejados?\b|\bplantas?\b|\bmaceteros?\b|\bmacetas?\b|\bmangueras?\b|\bcortadoras? de pasto\b|\bpodadoras?\b|\bparrillas?\b|\bquinchos?\b|\bbbq\b|\bpiscinas?\b|\bterrazas?\b|\btutor(es)? (para )?plantas?|\bsemillas?\b|\btierra de hoja\b|\bquitasol(es)?\b|\breposeras?\b|\bjuegos? de terraza\b|\bfertilizantes?\b|\babono\b|\bregaderas?\b|\baspersor(es)?\b|\bmotosierras?\b|\bdesbrozadoras?\b|\bsopladoras?\b|\bcarbon\b|\bleñas?\b|\bhuertos?\b|\bpergolas?\b|\bgazebos?\b|\btoldos?\b|\bhamacas? (de )?jardin"),
    ("Ferretería y jardín", "Baño y cocina (construcción)", r"\bgriferias?\b|\bllaves? (de )?(lavaplatos|lavamanos|ducha|monomando)|\blavaplatos\b|\blavamanos\b|\bwc\b|\binodoros?\b|\bvanitorios?\b|\btinas?\b|\bduchas?\b|\bbarras? (de )?seguridad|\bbarras? (para )?discapacitados|\bcalefont\b|\btermos? electricos?\b|\bmonomandos?\b|\bsifon(es)?\b|\bmamparas?\b|\bceramicas?\b|\bporcelanatos?\b|\bpisos? (flotante|laminado|ceramico)"),
    ("Ferretería y jardín", "Seguridad y electricidad", r"\bcamaras? de seguridad\b|\bcerraduras?\b|\bchapas?\b|\balarmas?\b|\bdetector(es)? de humo|\bcajas? fuerte|\benchufes? inteligentes?|\binterruptor(es)?\b|\bcandados? (de )?seguridad|\bcitofonos?\b|\bmirillas?\b|\bsensor(es)? de movimiento"),
]
_REGLAS = [(cat, sub, re.compile(pat)) for cat, sub, pat in REGLAS]

# Respaldo cuando ninguna regla calza: la categoría general por palabras sueltas (sin subcategoría).
GENERALES = [
    ("Calzado", r"calzado|\bshoes?\b"),
    ("Vestuario", r"vestuario|\bropa\b|moda|apparel|clothing"),
    ("Accesorios", r"accesorio"),
    ("Deportes", r"deport|outdoor|\bsport"),
    ("Tecnología", r"tecnolog|electronic"),
    ("Electrohogar", r"electrohogar|electrodomest"),
    ("Muebles y hogar", r"\bhogar\b|\bhome\b|\bcasa\b|mueble|dormitorio|\bliving\b|cocina"),
    ("Belleza y salud", r"belleza|beauty|\bsalud\b|cosmet|farmacia"),
    ("Infantil", r"infantil|\bbebe\b|jugueter|\bkids?\b"),
    ("Mascotas", r"mascota|\bpets?\b"),
    ("Ferretería y jardín", r"ferreter|jardin|construcci"),
    ("Alimentos y bebidas", r"aliment|comida|despensa|gourmet|bebida|\bvino|abarrote|bodega de vinos|\bfood"),
]
_GENERALES = [(c, re.compile(p)) for c, p in GENERALES]


def _mejor_regla(texto):
    """La regla que calza más temprano en el texto (si empatan, la de coincidencia más larga)."""
    mejor = None
    for cat, sub, patron in _REGLAS:
        m = patron.search(texto)
        if m and (mejor is None or (m.start(), -(m.end() - m.start())) < (mejor[0], -mejor[1])):
            mejor = (m.start(), m.end() - m.start(), cat, sub)
    return mejor


def clasificar(nombre, *pistas):
    """Devuelve (categoría, subcategoría). `pistas`: categoría de la tienda, etiquetas, enlace…"""
    n = sin_tildes(nombre)
    m = _mejor_regla(n)
    if m:
        return m[2], m[3]
    resto = sin_tildes(" ".join(p for p in pistas if p)).replace("-", " ").replace("/", " ")
    m = _mejor_regla(resto)
    if m:
        return m[2], m[3]
    for cat, patron in _GENERALES:
        if patron.search(n) or patron.search(resto):
            return cat, ""
    return "Otros", ""


# ------------------------------------------------------------------ género
_GENERO = [
    ("Bebé", re.compile(r"\bbebes?\b|\bbaby\b|\bbabies\b|\brecien nacidos?\b|\bnewborn\b|\blactantes?\b|\b\d{1,2} ?(-|a) ?\d{1,2} meses\b")),
    ("Niña", re.compile(r"\bninas?\b|\bgirls?\b|\bteen girl\b|\bnena\b")),
    ("Niño", re.compile(r"\bninos?\b|\bboys?\b|\bteen boy\b")),
    ("Mujer", re.compile(r"\bmujer(es)?\b|\bdamas?\b|\bfemenin[oa]s?\b|\bwomen'?s?\b|\bwmns?\b|\blad(y|ies)\b|\bfemme\b|\bmaternal\b|\bmaternidad\b|\bpremama\b")),
    ("Hombre", re.compile(r"\bhombres?\b|\bvaron(es)?\b|\bcaballeros?\b|\bmasculin[oa]s?\b|\bmen'?s?\b|\bhomme\b")),
]
_INFANTIL = re.compile(r"\binfantil(es)?\b|\bkids?\b|\bjunior\b|\bjuvenil(es)?\b|\bnin[oa]s\b|\bchildren\b|\bescolar\b|\byouth\b|\bteens?\b")
_UNISEX = re.compile(r"\bunisex\b")


def genero(nombre, *pistas):
    """Lista de géneros del producto (vacía si no se sabe). Unisex cuenta para Mujer y Hombre."""
    for texto in (sin_tildes(nombre), sin_tildes(" ".join(p for p in pistas if p)).replace("-", " ").replace("/", " ")):
        encontrados = [g for g, patron in _GENERO if patron.search(texto)]
        if _UNISEX.search(texto):
            encontrados += ["Mujer", "Hombre"]
        if not encontrados and _INFANTIL.search(texto):
            encontrados = ["Niña", "Niño"]
        if encontrados:
            return sorted(set(encontrados), key=["Mujer", "Hombre", "Niña", "Niño", "Bebé"].index)
    return []


# ------------------------------------------------------------------ tallas
ORDEN_LETRAS = ["XXS", "XS", "S", "M", "L", "XL", "XXL", "3XL", "4XL", "5XL"]
_ALIAS = {"2XL": "XXL", "XXXL": "3XL", "XXXXL": "4XL", "EXTRA SMALL": "XS", "SMALL": "S", "MEDIUM": "M",
          "MEDIANO": "M", "MEDIANA": "M", "LARGE": "L", "EXTRA LARGE": "XL", "CHICO": "S", "CHICA": "S",
          "GRANDE": "L", "XG": "XL", "XXG": "XXL", "P": "S", "G": "L"}
_UNICA = {"U", "TU", "UNICA", "UNICO", "TALLA UNICA", "ONE SIZE", "OS", "STD", "ESTANDAR", "UNI", "T/U", "OSFA"}
_LETRA = r"(?:XXS|XS|S|M|L|XL|XXL|3XL|4XL|5XL)"


def normalizar_talla(valor):
    """Convierte una talla al formato del sitio, o None si no parece talla (colores, medidas, etc.)."""
    t = sin_tildes(str(valor or "")).upper().strip()
    t = re.sub(r"^(TALLAS?|TALLE|TALLA:|N[°ºO]?\.?|NRO\.?|NUMERO|T\.|T-)\s*", "", t).strip()
    t = re.sub(r"\s*(CL|CHI|EU|EUR|AR|BR)$", "", t).strip().replace(",", ".")
    if not t:
        return None
    if t in _UNICA:
        return "Única"
    m = re.fullmatch(r"(1[5-9]|[2-4]\d)(0|5)", t)  # "395" = 39.5 (algunas tiendas escriben el número sin punto)
    if m:
        return m.group(1) + (".5" if m.group(2) == "5" else "")
    m = re.fullmatch(r"M?(\d{1,2})\s*W(\d{1,2})", t)  # Crocs: "3W5" = hombre 3 / mujer 5
    if m:
        return "M" + m.group(1) + "/W" + m.group(2)
    if re.fullmatch(r"C\d{1,2}|J\d{1,2}", t):  # Crocs niños: C4, J2
        return t
    t = _ALIAS.get(t, t)
    if re.fullmatch(_LETRA, t):
        return t
    if re.fullmatch(_LETRA + r"\s*[/-]\s*" + _LETRA, t):
        return re.sub(r"\s*[/-]\s*", "/", t)
    if re.fullmatch(r"\d{1,2}(\.5)?", t) and 0 < float(t) <= 60:
        return t.rstrip("0").rstrip(".") if "." in t else str(int(t))
    m = re.fullmatch(r"(\d{1,2})\s*[-/]\s*(\d{1,2})\s*(M|MESES|A|ANOS)?", t)
    if m and int(m.group(1)) < int(m.group(2)):
        return m.group(1) + "/" + m.group(2) + (m.group(3) or "")[:1]
    m = re.fullmatch(r"(\d{1,2})\s*(M|MESES|MES)", t)
    if m:
        return m.group(1) + "M"
    m = re.fullmatch(r"(\d{1,2})\s*(A|ANOS?|Y|YEARS?)", t)
    if m:
        return m.group(1) + "A"
    return None


def clave_talla(t):
    """Orden para mostrar: letras, Única, números, meses, años."""
    primera = t.split("/")[0]
    if primera in ORDEN_LETRAS:
        return (0, ORDEN_LETRAS.index(primera) + (0.5 if "/" in t else 0))
    if t == "Única":
        return (1, 0)
    if re.fullmatch(r"[CJ]\d+|M\d+/W\d+", t):
        return (6 if t[0] != "M" else 7, float(re.search(r"\d+", t).group(0)))
    n = re.match(r"\d+(\.\d+)?", t)
    numero = float(n.group(0)) if n else 0
    if t.endswith("M"):
        return (3, numero)
    if t.endswith("A"):
        return (4, numero)
    return (2, numero) if n else (5, 0)


def tallas(valores):
    vistas = {normalizar_talla(v) for v in valores}
    vistas.discard(None)
    return sorted(vistas, key=clave_talla)


ES_OPCION_TALLA = re.compile(r"talla|talle|size|numero|número|\bn[°º]|calce|tamano|tamaño|cintura|waist", re.I)


TALLA_EN_NOMBRE = re.compile(r"\btalla\s+(\d{2}(?:[.,]5)?|XXS|XS|S|M|L|XL|XXL|unica|única)\b", re.I)
CON_TALLAS = {"Vestuario", "Calzado", "Accesorios", "Deportes"}
