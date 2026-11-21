from agent.preguntas_locales import calculo_dictado, preguntas_multiples


def test_comprension_acotada_de_preguntas_y_dictado():
    assert preguntas_multiples("¿Qué hora es? Y ¿Cuánto es dos más dos?") == [
        "¿Qué hora es?", "¿Cuánto es dos más dos?"]
    assert not preguntas_multiples("¿Qué hora es? Cierra la ventana?")
    assert calculo_dictado("Cuanto es dos mas dos") == "2 + 2"
    assert calculo_dictado("Calcula 12 por cinco menos uno") == "12 * 5 - 1"
    assert calculo_dictado("Calcula y abre dos aplicaciones") is None
